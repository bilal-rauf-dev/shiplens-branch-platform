"""Validate portable CSV headers, then replay an atomic historical service log."""

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import yaml
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps import audit
from apps.accounts import services as accounts
from apps.accounts.models import Role, User
from apps.audit.context import request_context
from apps.branches import services as branches
from apps.branches.models import Branch, City
from apps.cms import services as cms
from apps.cms.models import ContentStatus
from apps.core import clock
from apps.finance import report_services
from apps.finance import services as finance
from apps.finance.models import Collection, WeeklyReport
from apps.seed.reference_data import restore_reference_data
from apps.volunteers import services as volunteers
from apps.volunteers.models import Application, Member, Team, VolunteerRole

HEADERS = {
    "content": (
        "type,slug,status,sort_order,image,event_start,event_end,location_en,location_ur,"
        "title_en,summary_en,body_en,title_ur,summary_ur,body_ur"
    ),
    "cities": "code,name_en,name_ur",
    "branches": (
        "branch_code,city_code,name_en,name_ur,address_en,address_ur,phone,email,"
        "target_status"
    ),
    "users": "email,full_name,role",
    "assignments": "user_email,branch_code",
    "teams": "branch_code,name",
    "members": (
        "member_order,full_name,email,phone,branch_code,team_name,role_code,"
        "target_status,joined_on,left_on"
    ),
    "applications": (
        "application_order,full_name,email,phone,date_of_birth,branch_code,"
        "interests,availability,motivation,preferred_language,received_on,"
        "target_status,decided_on,decision_note,team_name,role_code"
    ),
    "collections": (
        "ref,branch_code,collection_date,amount,method,receipt_no,created_at,"
        "voided_at,void_reason"
    ),
    "transfers": "ref,branch_code,transfer_date,bank_reference,receipt_numbers",
    "reports": (
        "ref,branch_code,week_start,target_status,activities,volunteer_hours,issues"
    ),
    "events": "timestamp,actor_email,action,arguments",
}


def read_dataset(directory, mapping_path=None):
    """Report every missing or unknown header before touching the database."""
    mapping = {}
    if mapping_path:
        mapping = yaml.safe_load(Path(mapping_path).read_text(encoding="utf-8"))
        if not isinstance(mapping, dict):
            raise ValueError(
                "The mapping must be a YAML mapping of filenames to columns."
            )
        unknown = mapping.keys() - {f"{name}.csv" for name in HEADERS}
        if unknown:
            raise ValueError(f"Unknown mapping files: {sorted(unknown)}")
    tables, errors = {}, []
    for name, columns in HEADERS.items():
        filename = f"{name}.csv"
        aliases = mapping.get(filename, {})
        if not isinstance(aliases, dict) or any(
            not isinstance(key, str) or value not in columns.split(",")
            for key, value in aliases.items()
        ):
            raise ValueError(f"Invalid column mapping for {filename}")
        try:
            with (Path(directory) / filename).open(
                encoding="utf-8-sig", newline=""
            ) as source:
                reader = csv.DictReader(source)
                headers = [aliases.get(key, key) for key in reader.fieldnames or []]
                required = set(columns.split(","))
                missing, unknown = required - set(headers), set(headers) - required
                if missing or unknown or len(headers) != len(set(headers)):
                    errors.append(
                        f"{filename}: missing columns {sorted(missing)}; "
                        f"unknown columns {sorted(unknown)}; "
                        f"duplicate columns {len(headers) != len(set(headers))}"
                    )
                    continue
                tables[name] = []
                for line, row in enumerate(reader, 2):
                    if None in row or None in row.values():
                        raise ValueError(f"{filename}:{line}: wrong number of cells")
                    tables[name].append(
                        {aliases.get(key, key): value for key, value in row.items()}
                    )
        except FileNotFoundError:
            errors.append(f"{filename}: missing file")
    if errors:
        raise ValueError("Invalid sample-data headers:\n" + "\n".join(errors))
    return tables


def _row(tables, table, key, value):
    matches = [item for item in tables[table] if item[key] == str(value)]
    if len(matches) != 1:
        raise ValueError(f"Expected one {table} row with {key}={value!r}")
    return matches[0]


def _branch(code):
    return Branch.objects.get(code=code)


def _team(branch, name):
    return Team.objects.get(branch=branch, name=name) if name else None


def _member(order):
    return Member.objects.get(member_id=f"M-{clock.today().year}-{int(order):05d}")


def _application(order):
    return Application.objects.get(
        reference=f"APP-{clock.today().year}-{int(order):05d}"
    )


def _user_event(actor, row):
    """Bootstrap the first administrator; all later users use account services."""
    if actor is None:
        if User.objects.exists() or row["role"] != Role.SUPER_ADMIN:
            raise ValueError(
                "Bootstrap requires an empty user table and a Super Admin."
            )
        restore_reference_data()
        user = User.objects.create_user(**row)
        audit.record(
            None,
            "user.created",
            entity=user,
            after={"email": user.email, "role": user.role},
        )
    else:
        user, _temporary = accounts.create_user(actor, **row)
    return user


def replay_event(tables, actor, action, args):
    """Resolve natural keys explicitly and call the existing domain service."""
    if action == "user.create":
        _user_event(actor, _row(tables, "users", "email", args["email"]))
    elif action == "city.ensure":
        row = _row(tables, "cities", "code", args["code"])
        if not City.objects.filter(code=row["code"]).exists():
            branches.create_city(actor, **row)
    elif action == "branch.create":
        row = _row(tables, "branches", "branch_code", args["branch_code"])
        item = branches.create_branch(
            actor,
            city=City.objects.get(code=row["city_code"]),
            **{key: row[key] for key in branches.EDITABLE_FIELDS},
        )
        if item.code != row["branch_code"]:
            raise ValueError(f"Unexpected branch counter: {item.code}")
    elif action == "assignment.create":
        if args not in tables["assignments"]:
            raise ValueError("The assignment must exist in assignments.csv")
        accounts.assign_branch(
            actor,
            User.objects.get(email=args["user_email"]),
            _branch(args["branch_code"]),
        )
    elif action in {"branch.activate", "branch.pause", "branch.close"}:
        branches.transition(
            actor,
            _branch(args["branch_code"]),
            action.split(".")[1],
            reason=args.get("reason", ""),
        )
    elif action == "team.create":
        if args not in tables["teams"]:
            raise ValueError("The team must exist in teams.csv")
        volunteers.create_team(
            actor, _branch(args["branch_code"]).pk, name=args["name"]
        )
    elif action == "member.import":
        row = _row(tables, "members", "member_order", args["member_order"])
        branch = _branch(row["branch_code"])
        member = volunteers.import_member(
            actor,
            branch=branch,
            team=_team(branch, row["team_name"]),
            volunteer_role=VolunteerRole.objects.get(code=row["role_code"]),
            full_name=row["full_name"],
            email=row["email"],
            phone=row["phone"],
            joined_on=date.fromisoformat(row["joined_on"]),
        )
        if member.member_id != f"M-{clock.today().year}-{int(row['member_order']):05d}":
            raise ValueError("Unexpected member counter")
    elif action in {"member.mark_left", "member.deactivate"}:
        volunteers.transition_member(
            actor,
            _member(args["member_order"]).pk,
            action.split(".")[1],
            left_on=date.fromisoformat(args["left_on"])
            if args.get("left_on")
            else None,
        )
    elif action == "collection.create":
        row = _row(tables, "collections", "receipt_no", args["receipt_no"])
        if clock.now() != datetime.fromisoformat(row["created_at"]):
            raise ValueError("Collection event must match created_at")
        finance.create_collection(
            actor,
            _branch(row["branch_code"]),
            {
                "collection_date": date.fromisoformat(row["collection_date"]),
                "amount": Decimal(row["amount"]),
                "method": row["method"],
                "receipt_no": row["receipt_no"],
            },
        )
    elif action == "collection.void":
        row = _row(tables, "collections", "receipt_no", args["receipt_no"])
        if clock.now() != datetime.fromisoformat(row["voided_at"]):
            raise ValueError("Void event must match voided_at")
        finance.void_collection(
            actor,
            Collection.objects.get(
                branch__code=row["branch_code"], receipt_no=row["receipt_no"]
            ),
            row["void_reason"],
        )
    elif action == "transfer.create":
        row = _row(tables, "transfers", "ref", args["ref"])
        branch = _branch(row["branch_code"])
        receipts = row["receipt_numbers"].split(";")
        items = list(Collection.objects.filter(branch=branch, receipt_no__in=receipts))
        if len(items) != len(receipts):
            raise ValueError("Transfer references missing or duplicate receipts")
        finance.create_transfer(
            actor,
            branch,
            [item.pk for item in items],
            date.fromisoformat(row["transfer_date"]),
            row["bank_reference"],
        )
    elif action == "application.submit":
        row = _row(
            tables, "applications", "application_order", args["application_order"]
        )
        application = volunteers.submit_application(
            {
                **{
                    key: row[key]
                    for key in (
                        "full_name",
                        "email",
                        "phone",
                        "motivation",
                        "preferred_language",
                    )
                },
                "date_of_birth": date.fromisoformat(row["date_of_birth"]),
                "guardian_consent": False,
                "privacy_consent": True,
                "interests": row["interests"].split(";"),
                "availability": row["availability"].split(";"),
                "preferred_branch": _branch(row["branch_code"]),
            },
            request_ip=None,
        )
        if (
            application.reference
            != f"APP-{clock.today().year}-{int(row['application_order']):05d}"
        ):
            raise ValueError("Unexpected application counter")
    elif action in {"application.accept", "application.decline"}:
        row = _row(
            tables, "applications", "application_order", args["application_order"]
        )
        application = _application(args["application_order"])
        if action == "application.accept":
            team = _team(application.preferred_branch, row["team_name"])
            volunteers.accept_application(
                actor,
                application.pk,
                team_id=team.pk if team else None,
                role_id=VolunteerRole.objects.get(code=row["role_code"]).pk,
            )
        else:
            volunteers.decline_application(actor, application.pk, row["decision_note"])
    elif action == "report.ensure_drafts":
        report_services.ensure_drafts(
            _branch(args["branch_code"]),
            week_start=date.fromisoformat(args["week_start"]),
        )
    elif action in {
        "report.submit",
        "report.resubmit",
        "report.return",
        "report.approve",
    }:
        row = _row(tables, "reports", "ref", args["ref"])
        branch, week = (
            _branch(row["branch_code"]),
            date.fromisoformat(row["week_start"]),
        )
        if action == "report.submit":
            report_services.ensure_drafts(branch, week_start=week)
        report = WeeklyReport.objects.get(branch=branch, week_start=week)
        narrative = {
            "activities": row["activities"],
            "volunteer_hours": int(row["volunteer_hours"]),
            "issues": row["issues"],
        }
        report_services.transition(
            actor,
            report,
            action.split(".")[1],
            expected_revision=report.revision,
            comment=args.get("comment", ""),
            narrative=narrative
            if action in {"report.submit", "report.resubmit"}
            else None,
        )
    else:
        raise ValueError(f"Unknown historical action: {action}")


def import_sample_data(directory, mapping_path=None):
    """Validate first, then commit the complete chronological history or nothing."""
    tables = read_dataset(directory, mapping_path)
    events = []
    for line, row in enumerate(tables["events"], 2):
        instant = datetime.fromisoformat(row["timestamp"])
        if timezone.is_naive(instant):
            raise ValueError(f"events.csv:{line}: timestamp must include an offset")
        events.append((instant, line, row))
    token = request_context.set(None)
    try:
        with transaction.atomic():
            for instant, line, row in sorted(events, key=lambda item: item[0]):
                try:
                    with clock.frozen_at(instant):
                        actor = (
                            User.objects.get(email=row["actor_email"])
                            if row["actor_email"]
                            else None
                        )
                        replay_event(
                            tables, actor, row["action"], json.loads(row["arguments"])
                        )
                except Exception as error:
                    raise ValidationError(
                        f"events.csv:{line} {row['action']}: {error}"
                    ) from error
            actor = User.objects.get(role=Role.CONTENT_EDITOR)
            # Keep imported audit timestamps chronological after the authored timeline.
            with clock.frozen_at(max(event[0] for event in events)):
                for row in tables["content"]:
                    item = cms.create(
                        actor,
                        type=row["type"],
                        slug=row["slug"],
                        sort_order=int(row["sort_order"]),
                        image_path=row["image"],
                        event_start=datetime.fromisoformat(row["event_start"])
                        if row["event_start"]
                        else None,
                        event_end=datetime.fromisoformat(row["event_end"])
                        if row["event_end"]
                        else None,
                        location_en=row["location_en"],
                        location_ur=row["location_ur"],
                        translations={
                            locale: {
                                "title": row[f"title_{locale}"],
                                "summary": row[f"summary_{locale}"],
                                "body_md": row[f"body_{locale}"],
                            }
                            for locale in ("en", "ur")
                        },
                    )
                    if row["status"] == ContentStatus.PUBLISHED:
                        cms.transition(actor, item.pk, "publish")
                    elif row["status"] == ContentStatus.ARCHIVED:
                        cms.transition(actor, item.pk, "archive")
                    elif row["status"] != ContentStatus.DRAFT:
                        raise ValidationError("Unknown content target status")
    finally:
        request_context.reset(token)
    return {name: len(rows) for name, rows in tables.items()}
