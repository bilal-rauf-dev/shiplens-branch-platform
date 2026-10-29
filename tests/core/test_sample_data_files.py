"""The authored files are portable, fictional, and reference natural keys."""

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "sample_data"


def rows(name):
    with (ROOT / f"{name}.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_sample_dataset_row_counts_and_natural_keys():
    expected = {
        "cities": 5,
        "branches": 5,
        "users": 8,
        "assignments": 7,
        "teams": 3,
        "members": 9,
        "applications": 8,
        "collections": 15,
        "transfers": 7,
        "reports": 10,
        "events": 102,
        "content": 12,
    }
    for name, count in expected.items():
        records = rows(name)
        assert len(records) == count, name
        assert not {"id", "password", "branch_id", "user_id"} & records[0].keys()
    assert [row["member_order"] for row in rows("members")] == [
        str(number) for number in range(1, 10)
    ]
    assert rows("applications")[7]["email"] == rows("members")[8]["email"]


def test_sample_applicants_are_fictional_adults():
    for row in rows("applications"):
        born = date.fromisoformat(row["date_of_birth"])
        received = date.fromisoformat(row["received_on"])
        age = (
            received.year
            - born.year
            - ((received.month, received.day) < (born.month, born.day))
        )
        assert 18 <= age <= 35
        assert row["email"].endswith("@example.org")
        assert row["phone"].startswith("+923000000")


def test_sample_timeline_has_aware_pkt_timestamps_and_known_actors():
    actors = {row["email"] for row in rows("users")} | {""}
    previous = None
    for row in rows("events"):
        instant = datetime.fromisoformat(row["timestamp"])
        assert instant.utcoffset() == timedelta(hours=5)
        assert previous is None or instant >= previous
        assert row["actor_email"] in actors
        assert isinstance(json.loads(row["arguments"]), dict)
        previous = instant
