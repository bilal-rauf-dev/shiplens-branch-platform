from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.generic import DetailView, FormView, ListView

from apps.accounts.permissions import can, require, scope_queryset
from apps.core import clock
from apps.core.exceptions import InvalidTransition
from apps.core.views import PermissionRequiredMixin
from apps.finance import selectors, services
from apps.finance.forms import CollectionFilterForm, CollectionForm, VoidCollectionForm


def add_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class CollectionListView(PermissionRequiredMixin, ListView):
    required_action = "collection.list"
    template_name = "finance/collection_list.html"
    context_object_name = "collections"
    paginate_by = 25

    def get_queryset(self):
        self.filter_form = CollectionFilterForm(self.request.GET)
        queryset = (
            selectors.search_collections(
                self.request.user, self.filter_form.cleaned_data
            )
            if self.filter_form.is_valid()
            else selectors.collections().none()
        )
        self.totals = selectors.totals(queryset)
        return queryset

    def get_context_data(self, **kwargs):
        params = self.request.GET.copy()
        params.pop("page", None)
        return {
            **super().get_context_data(**kwargs),
            "filter_form": self.filter_form,
            "totals": self.totals,
            "managed_branches": selectors.managed_branches(self.request.user),
            "filter_query": params.urlencode(),
        }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class CollectionDetailView(PermissionRequiredMixin, DetailView):
    required_action = "collection.view"
    queryset = selectors.collections()
    template_name = "finance/collection_detail.html"
    context_object_name = "collection"

    def get_context_data(self, **kwargs):
        item = self.object
        return {
            **super().get_context_data(**kwargs),
            "can_edit": can(self.request.user, "collection.update", item),
            "can_void": can(self.request.user, "collection.void", item),
            "void_form": VoidCollectionForm(),
            "show_history": can(self.request.user, "audit.entity_history", item),
            "history": selectors.history(self.request.user, item),
        }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class CollectionCreateView(PermissionRequiredMixin, FormView):
    required_action = "collection.create"
    form_class = CollectionForm
    template_name = "finance/collection_form.html"
    extra_context = {"page_title": _("Create collection")}

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.branch = get_object_or_404(
            selectors.managed_branches(request.user), pk=kwargs["branch_pk"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "branch": self.branch}

    def get_initial(self):
        return {"collection_date": clock.today()}

    def form_valid(self, form):
        try:
            item = services.create_collection(
                self.request.user, self.branch, form.cleaned_data
            )
        except InvalidTransition as error:
            form.add_error(None, str(error))
            return self.render_to_response(self.get_context_data(form=form), status=409)
        except ValidationError as error:
            add_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Collection created."))
        return redirect("collection-detail", pk=item.pk)


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class CollectionEditView(PermissionRequiredMixin, FormView):
    required_action = "collection.update"
    form_class = CollectionForm
    template_name = "finance/collection_form.html"
    extra_context = {"page_title": _("Edit collection")}

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.collection = get_object_or_404(
            scope_queryset(request.user, self.required_action, selectors.collections()),
            pk=kwargs["pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "branch": self.collection.branch}

    def get_initial(self):
        item = self.collection
        return {
            "collection_date": item.collection_date,
            "amount": item.amount,
            "method": item.method,
            "receipt_no": item.receipt_no,
            "collected_by": item.collected_by_member_id,
            "source_note": item.source_note,
        }

    def form_valid(self, form):
        try:
            services.update_collection(
                self.request.user, self.collection, form.cleaned_data
            )
        except InvalidTransition as error:
            form.add_error(None, str(error))
            return self.render_to_response(self.get_context_data(form=form), status=409)
        except ValidationError as error:
            add_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Collection updated."))
        return redirect("collection-detail", pk=self.collection.pk)


class CollectionVoidView(CollectionEditView):
    required_action = "collection.void"
    form_class = VoidCollectionForm
    extra_context = {"page_title": _("Void collection")}

    def get_form_kwargs(self):
        return FormView.get_form_kwargs(self)

    def get_initial(self):
        return {}

    def form_valid(self, form):
        try:
            services.void_collection(
                self.request.user, self.collection, form.cleaned_data["reason"]
            )
        except InvalidTransition as error:
            form.add_error(None, str(error))
            return self.render_to_response(self.get_context_data(form=form), status=409)
        except ValidationError as error:
            add_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Collection voided."))
        return redirect("collection-detail", pk=self.collection.pk)
