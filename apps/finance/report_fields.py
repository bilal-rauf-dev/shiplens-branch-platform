"""BR-084: adding a narrative field requires one REPORT_FIELDS registry entry.

The form reads labels, types and validation bounds from this explicit data. Services
use the same form to validate direct calls; no separate validation table can drift.
"""

from django.utils.translation import gettext_lazy as _

REPORT_FIELDS = {
    "activities": {
        "type": "text",
        "label": _("Activities"),
        "required": True,
        "min_length": 10,
        "max_length": 2000,
    },
    "volunteer_hours": {
        "type": "integer",
        "label": _("Volunteer hours"),
        "required": True,
        "min_value": 0,
        "max_value": 10000,
    },
    "issues": {
        "type": "text",
        "label": _("Issues"),
        "required": False,
        "max_length": 2000,
    },
}
