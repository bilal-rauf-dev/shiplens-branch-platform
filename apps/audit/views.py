import json

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.audit import selectors, services
from apps.audit.forms import AuditFilterForm
from apps.core.views import PermissionRequiredMixin


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class AuditListView(PermissionRequiredMixin, ListView):
    required_action = "audit.list"
    template_name = "audit/event_list.html"
    context_object_name = "events"
    paginate_by = 50

    def get_queryset(self):
        self.filter_form = AuditFilterForm(self.request.GET, user=self.request.user)
        if not self.filter_form.is_valid():
            return selectors.events().none()
        return selectors.search_events(self.request.user, self.filter_form.cleaned_data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        return {
            **context,
            "filter_form": self.filter_form,
            "filter_query": params.urlencode(),
            "rows": selectors.viewer_rows(self.request.user, context["events"]),
        }


@method_decorator(cache_control(no_store=True, private=True), name="dispatch")
class AuditDetailView(PermissionRequiredMixin, DetailView):
    required_action = "audit.view"
    queryset = selectors.events()
    template_name = "audit/event_detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "row": selectors.viewer_rows(self.request.user, [self.object])[0],
            "changes": selectors.changed_fields(self.object),
            "metadata": json.dumps(
                self.object.metadata, ensure_ascii=False, sort_keys=True, indent=2
            ),
        }


@cache_control(no_store=True, private=True)
@require_POST
def verify(request):
    intact, broken_id, count = services.verify_and_record(request.user)
    if intact:
        messages.success(
            request, _("Chain intact (%(count)s events)") % {"count": count}
        )
    else:
        messages.error(request, _("Chain broken at event #%(id)s") % {"id": broken_id})
    return redirect("audit-list")
