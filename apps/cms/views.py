from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.generic import DetailView, FormView, ListView

from apps.accounts.permissions import require, scope_queryset
from apps.cms import selectors, services
from apps.cms.forms import ContentFilterForm, ContentForm
from apps.cms.models import ContentType
from apps.core.exceptions import InvalidTransition
from apps.core.views import PermissionRequiredMixin
from apps.finance.views import add_errors


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ContentListView(PermissionRequiredMixin, ListView):
    required_action = "content.list"
    template_name = "cms/list.html"
    context_object_name = "items"
    queryset = selectors.items()

    def get_queryset(self):
        params = self.request.GET.copy()
        params.setdefault("type", ContentType.PAGE_SECTION)
        self.filter_form = ContentFilterForm(params)
        rows = super().get_queryset()
        if not self.filter_form.is_valid():
            return rows.none()
        for name in ("type", "status"):
            if self.filter_form.cleaned_data.get(name):
                rows = rows.filter(**{name: self.filter_form.cleaned_data[name]})
        return rows

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "filter_form": self.filter_form,
            "types": ContentType.choices,
            "current_type": self.filter_form.data.get("type"),
        }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ContentEditView(PermissionRequiredMixin, FormView):
    required_action = "content.create"
    form_class = ContentForm
    template_name = "cms/editor.html"

    def dispatch(self, request, *args, **kwargs):
        require(request.user, self.required_action)
        self.item = None
        if "pk" in kwargs:
            self.item = get_object_or_404(
                scope_queryset(request.user, self.required_action, selectors.items()),
                pk=kwargs["pk"],
            )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        if not self.item:
            return {
                "type": self.request.GET.get("type", ContentType.PAGE_SECTION),
                "sort_order": 0,
            }
        initial = {
            field: getattr(self.item, field)
            for field in ("type", *services.EDITABLE)
            if field != "branch"
        }
        for row in self.item.translations.all():
            initial.update(
                {
                    f"title_{row.locale}": row.title,
                    f"summary_{row.locale}": row.summary,
                    f"body_{row.locale}": row.body_md,
                }
            )
        return initial

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "item": self.item}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item"] = self.item
        return context

    def form_valid(self, form):
        values = form.service_data()
        try:
            if self.item:
                values.pop("type")
                item = services.update(self.request.user, self.item.pk, **values)
            else:
                item = services.create(self.request.user, **values)
        except ValidationError as error:
            add_errors(form, error)
            return self.form_invalid(form)
        except InvalidTransition as error:
            form.add_error(None, str(error))
            return self.render_to_response(self.get_context_data(form=form), status=409)
        messages.success(self.request, _("Working copy saved."))
        return redirect("content-edit", pk=item.pk)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form), status=400)


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class ContentPreviewView(PermissionRequiredMixin, DetailView):
    required_action = "content.view"
    queryset = selectors.items()
    template_name = "cms/preview.html"
    context_object_name = "item"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "copy": selectors.localize(
                selectors.working_snapshot(self.object), self.request.LANGUAGE_CODE
            ),
        }


class ContentTransitionView(ContentPreviewView):
    operation = None
    template_name = "cms/confirm.html"

    def get_context_data(self, **kwargs):
        labels = {
            "publish": _("Publish"),
            "unpublish": _("Unpublish"),
            "archive": _("Archive"),
            "restore": _("Restore"),
        }
        return {
            **super().get_context_data(**kwargs),
            "operation": self.operation,
            "operation_label": labels[self.operation],
            "destructive": self.operation in {"unpublish", "archive"},
        }

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            services.transition(request.user, self.object.pk, self.operation)
        except (ValidationError, InvalidTransition) as error:
            text = (
                " ".join(error.messages)
                if isinstance(error, ValidationError)
                else str(error)
            )
            return self.render_to_response(
                self.get_context_data(error=text),
                status=400 if isinstance(error, ValidationError) else 409,
            )
        messages.success(request, _("Content state updated."))
        return redirect("content-list")
