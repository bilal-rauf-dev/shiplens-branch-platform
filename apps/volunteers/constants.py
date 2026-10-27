from django.utils.translation import gettext_lazy as _

# P10 replaces these choices with published programs plus "general".
INTERESTS = [
    ("education", _("Education")),
    ("ration-drive", _("Ration drive")),
    ("health-camps", _("Health camps")),
    ("general", _("General volunteering")),
]
AVAILABILITY = [
    ("weekday_mornings", _("Weekday mornings")),
    ("weekday_evenings", _("Weekday evenings")),
    ("weekends", _("Weekends")),
]
