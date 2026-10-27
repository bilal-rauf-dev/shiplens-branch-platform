from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import DetailView, FormView, ListView

from apps.accounts.permissions import can, require, scope_queryset
from apps.core import clock
from apps.core.exceptions import InvalidTransition
from apps.core.views import PermissionRequiredMixin
from apps.finance import selectors, services
from apps.finance.forms import (
    CollectionFilterForm,
    CollectionForm,
    TransferForm,
    TransferSelectionForm,
    VoidCollectionForm,
)


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
            "can_transfer": can(self.request.user, "transfer.create")
            and self.filter_form.is_valid()
            and self.filter_form.cleaned_data.get("state") == "UNSENT",
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
            "can_edit": can(self.request.user, "collection.update", item)
            and item.state == "OPEN",
            "can_void": can(self.request.user, "collection.void", item)
            and item.state == "OPEN",
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


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class TransferListView(PermissionRequiredMixin, ListView):
    required_action = "transfer.list"
    queryset = selectors.transfers()
    template_name = "finance/transfer_list.html"
    context_object_name = "transfers"
    paginate_by = 25

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "managed_branches": selectors.managed_branches(
                self.request.user, "transfer.create"
            ),
        }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class TransferDetailView(PermissionRequiredMixin, DetailView):
    required_action = "transfer.view"
    queryset = selectors.transfers()
    template_name = "finance/transfer_detail.html"
    context_object_name = "transfer"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "collections": scope_queryset(
                self.request.user, "collection.view", selectors.collections()
            ).filter(transfer=self.object),
        }


@cache_control(no_store=True, private=True)
@require_GET
def prepare_transfer(request):
    require(request.user, "transfer.create")
    form = TransferSelectionForm(request.GET, user=request.user)
    if form.is_valid():
        items = list(form.cleaned_data["collections"])
        from django.urls import reverse

        return redirect(
            reverse("transfer-create", kwargs={"branch_pk": items[0].branch_id})
            + "?"
            + urlencode({"collections": [item.pk for item in items]}, doseq=True)
        )
    from django.shortcuts import render

    return render(
        request, "finance/transfer_selection.html", {"form": form}, status=400
    )


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class TransferCreateView(PermissionRequiredMixin, FormView):
    required_action = "transfer.create"
    form_class = TransferForm
    template_name = "finance/transfer_form.html"

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.branch = get_object_or_404(
            selectors.managed_branches(request.user, self.required_action),
            pk=kwargs["branch_pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "branch": self.branch}

    def get_initial(self):
        return {
            "collections": self.request.GET.getlist("collections"),
            "transfer_date": clock.today(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_ids = (
            self.request.POST if self.request.method == "POST" else self.request.GET
        ).getlist("collections")
        selected = list(
            selectors.unsent(self.request.user).filter(
                branch=self.branch,
                pk__in=[
                    int(value)
                    for value in selected_ids
                    if value.isdecimal() and int(value).bit_length() <= 63
                ],
            )
        )
        if selected:
            context["form"].fields["transfer_date"].widget.attrs["min"] = max(
                item.collection_date for item in selected
            ).isoformat()
        return {
            **context,
            "branch": self.branch,
            "selected": selected,
            "selected_total": sum((item.amount for item in selected), Decimal("0.00")),
        }

    def form_invalid(self, form):
        ids = [
            int(value)
            for value in self.request.POST.getlist("collections")
            if value.isdecimal() and int(value).bit_length() <= 63
        ]
        conflict = selectors.selection_has_conflict(self.request.user, self.branch, ids)
        if conflict:
            form.add_error(None, _("A selected collection is voided or already sent."))
        return self.render_to_response(
            self.get_context_data(form=form), status=409 if conflict else 400
        )

    def form_valid(self, form):
        try:
            transfer = services.create_transfer(
                self.request.user,
                self.branch,
                list(form.cleaned_data["collections"].values_list("pk", flat=True)),
                form.cleaned_data["transfer_date"],
                form.cleaned_data["bank_reference"],
                form.cleaned_data["note"],
            )
        except InvalidTransition as error:
            form.add_error(None, str(error))
            return self.render_to_response(self.get_context_data(form=form), status=409)
        except ValidationError as error:
            add_errors(form, error)
            return self.form_invalid(form)
        messages.success(self.request, _("Transfer created."))
        return redirect("transfer-detail", pk=transfer.pk)


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
