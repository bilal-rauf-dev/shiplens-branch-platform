"""Shared form presentation; validation remains in each domain form."""

from django import forms


class Form(forms.Form):
    template_name_label = "core/forms/label.html"

    def __init__(self, *args, **kwargs):
        kwargs["label_suffix"] = ""
        super().__init__(*args, **kwargs)
