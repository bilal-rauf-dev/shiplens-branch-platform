"""Password changes expose a signal for the audit handlers added in P2 Step 4."""

from django.dispatch import Signal

password_changed = Signal()
