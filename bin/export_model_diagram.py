"""Refresh the architecture ER diagram from Django's application models."""

import os
import sys
from pathlib import Path

import django
from django.apps import apps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")


def model_diagram():
    """Include concrete fields and every FK, including nullable and self links."""
    models = sorted(
        (model for model in apps.get_models() if model.__module__.startswith("apps.")),
        key=lambda model: model._meta.db_table,
    )
    lines = ["```mermaid", "erDiagram"]
    for model in models:
        lines.append(f"    {model._meta.db_table} {{")
        for field in model._meta.concrete_fields:
            kind = field.get_internal_type()
            key = " PK" if field.primary_key else " FK" if field.is_relation else ""
            lines.append(f"        {kind} {field.column}{key}")
        lines.append("    }")
    for model in models:
        for field in model._meta.concrete_fields:
            if not field.is_relation:
                continue
            parent = field.related_model._meta.db_table
            parent_end = "|o" if field.null else "||"
            child_end = "o|" if field.one_to_one else "o{"
            lines.append(
                f"    {parent} {parent_end}--{child_end} "
                f'{model._meta.db_table} : "{field.name}"'
            )
    lines.append("```")
    return "\n".join(lines)


def main():
    django.setup()
    path = ROOT / "docs" / "architecture.md"
    source = path.read_text(encoding="utf-8")
    before, rest = source.split("<!-- ER:START -->", 1)
    _, after = rest.split("<!-- ER:END -->", 1)
    path.write_text(
        before + "<!-- ER:START -->\n" + model_diagram() + "\n<!-- ER:END -->" + after,
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
