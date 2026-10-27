from django.urls import path

from apps.volunteers import views

urlpatterns = [
    path(
        "app/members/<int:pk>/edit/", views.MemberEditView.as_view(), name="member-edit"
    ),
    path(
        "app/members/<int:pk>/deactivate/",
        views.member_deactivate,
        name="member-deactivate",
    ),
    path(
        "app/members/<int:pk>/reactivate/",
        views.member_reactivate,
        name="member-reactivate",
    ),
    path(
        "app/members/<int:pk>/mark-left/",
        views.member_mark_left,
        name="member-mark-left",
    ),
    path(
        "app/members/<int:pk>/reinstate/",
        views.member_reinstate,
        name="member-reinstate",
    ),
    path("app/members/", views.MemberListView.as_view(), name="member-list"),
    path("app/teams/", views.TeamListView.as_view(), name="team-list"),
    path(
        "app/branches/<int:branch_pk>/teams/new/",
        views.TeamCreateView.as_view(),
        name="team-create",
    ),
    path("app/teams/<int:pk>/edit/", views.TeamEditView.as_view(), name="team-edit"),
    path(
        "app/teams/<int:pk>/deactivate/", views.deactivate_team, name="team-deactivate"
    ),
    path(
        "app/volunteer-roles/",
        views.VolunteerRoleListView.as_view(),
        name="volunteer-role-list",
    ),
    path(
        "app/volunteer-roles/new/",
        views.VolunteerRoleCreateView.as_view(),
        name="volunteer-role-create",
    ),
    path(
        "app/volunteer-roles/<int:pk>/edit/",
        views.VolunteerRoleEditView.as_view(),
        name="volunteer-role-edit",
    ),
    path(
        "app/volunteer-roles/<int:pk>/deactivate/",
        views.deactivate_volunteer_role,
        name="volunteer-role-deactivate",
    ),
    path(
        "app/applications/",
        views.ApplicationListView.as_view(),
        name="application-list",
    ),
    path(
        "app/applications/<int:pk>/",
        views.ApplicationDetailView.as_view(),
        name="application-detail",
    ),
    path("app/applications/<int:pk>/accept/", views.accept, name="application-accept"),
    path(
        "app/applications/<int:pk>/decline/", views.decline, name="application-decline"
    ),
    path(
        "app/applications/<int:pk>/reassign/",
        views.reassign,
        name="application-reassign",
    ),
    path(
        "app/members/<int:pk>/", views.MemberDetailView.as_view(), name="member-detail"
    ),
    path("get-involved/", views.apply, name="volunteer-apply"),
    path("get-involved/thanks/", views.thanks, name="volunteer-thanks"),
]
