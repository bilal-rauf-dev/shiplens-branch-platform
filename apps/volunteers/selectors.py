from django.db.models import Q

from apps.branches.models import Branch, BranchStatus
from apps.volunteers.models import Application, ApplicationStatus, Member, MemberStatus


def accepting_branches():
    return (
        Branch.objects.filter(status__in=[BranchStatus.ACTIVE, BranchStatus.FORMING])
        .select_related("city")
        .order_by("city__code", "name_en", "pk")
    )


def duplicate_application(email, phone):
    return (
        Application.objects.filter(status=ApplicationStatus.PENDING)
        .filter(Q(email__iexact=email) | Q(phone=phone))
        .order_by("pk")
        .first()
    )


def duplicate_member(email, phone):
    return (
        Member.objects.exclude(status=MemberStatus.LEFT)
        .filter(Q(email__iexact=email) | Q(phone=phone))
        .order_by("pk")
        .first()
    )
