"""Public form responses expose a reference only, never duplicate or review data."""

import re
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.net import client_ip
from apps.volunteers import services
from apps.volunteers.forms import ApplicationForm


def _thanks(reference):
    return redirect(reverse("volunteer-thanks") + "?" + urlencode({"ref": reference}))


@cache_control(no_store=True)
@sensitive_post_parameters("full_name", "email", "phone", "date_of_birth", "motivation")
@require_http_methods(["GET", "POST"])
def apply(request):
    if request.method == "POST":
        if services.application_rate_limited(request):
            return render(request, "429.html", status=429)
        reason = services.spam_reason(request.POST)
        if reason is not None:
            return _thanks(services.discard_spam(reason))
        form = ApplicationForm(request.POST)
        if form.is_valid():
            try:
                application = services.submit_application(
                    form.cleaned_data, client_ip(request)
                )
            except ValidationError as error:
                for field, errors in error.message_dict.items():
                    form.add_error(field, errors)
            else:
                return _thanks(application.reference)
    else:
        form = ApplicationForm()
    return render(request, "volunteers/application_form.html", {"form": form})


@require_GET
def thanks(request):
    reference = request.GET.get("ref", "")
    if re.fullmatch(r"APP-[0-9]{4}-[0-9]{5,7}", reference) is None:
        reference = ""
    return render(request, "volunteers/thanks.html", {"reference": reference})
