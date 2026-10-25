"""Email identity and one explicit business role per user."""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.db import models, transaction
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.core import clock


class Role(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", _("Super Admin")
    FINANCE_REVIEWER = "FINANCE_REVIEWER", _("Finance Reviewer")
    CONTENT_EDITOR = "CONTENT_EDITOR", _("Content Editor")
    BRANCH_LEAD = "BRANCH_LEAD", _("Branch Lead")
    HR_LEAD = "HR_LEAD", _("HR Lead")


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).strip().lower()

    def get_by_natural_key(self, email):
        return self.get(email__iexact=self.normalize_email(email))

    def create_user(self, email, password=None, *, full_name, role, **extra_fields):
        """Create a validated identity with a password hash."""
        if not email:
            raise ValueError(_("An email address is required."))
        with transaction.atomic(using=self.db):
            user = self.model(
                email=self.normalize_email(email),
                full_name=full_name,
                role=role,
                **extra_fields,
            )
            if password is not None:
                validate_password(password, user=user)
            user.set_password(password)
            user.full_clean()
            user.save(using=self.db)
            return user

    def create_superuser(self, email, password=None, *, full_name, **extra_fields):
        """Support Django's bootstrap command using our Super Admin role only."""
        role = extra_fields.pop("role", Role.SUPER_ADMIN)
        if role != Role.SUPER_ADMIN or not extra_fields.get("is_active", True):
            raise ValueError(
                _("A Super Admin must be active and have the Super Admin role.")
            )
        return self.create_user(
            email, password, full_name=full_name, role=role, **extra_fields
        )


class User(AbstractBaseUser):
    # Field uniqueness supports Django checks; Lower rejects case variants as well.
    email = models.EmailField(_("email address"), max_length=254, unique=True)
    full_name = models.CharField(_("full name"), max_length=100)
    role = models.CharField(_("role"), max_length=20, choices=Role.choices)
    is_active = models.BooleanField(_("active"), default=True)
    is_demo = models.BooleanField(_("demo account"), default=False)
    must_change_password = models.BooleanField(_("must change password"), default=False)
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=5,
        choices=[("en", _("English")), ("ur", _("Urdu"))],
        default="en",
    )
    date_joined = models.DateTimeField(_("date joined"), default=clock.now)
    updated_at = models.DateTimeField(_("updated at"), default=clock.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.UniqueConstraint(Lower("email"), name="users_email_lower_unique"),
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values), name="users_role_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(preferred_language__in=["en", "ur"]),
                name="users_language_valid",
            ),
        ]

    def __str__(self):
        return self.email
