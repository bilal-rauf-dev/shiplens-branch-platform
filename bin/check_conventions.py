"""Check the repository's CSS direction and thin-view rules without extra tooling."""

import re
from pathlib import Path

PHYSICAL_CSS = re.compile(
    r"(?<![\w-])(?:"
    r"(?:margin|padding|border)-(?:left|right|top|bottom)\b"
    r"|(?:left|right|top|bottom|width|height|min-width|max-width|min-height|max-height)\s*:"
    r"|(?:margin|padding)\s*:"
    r"|text-align\s*:\s*(?:left|right)\b)"
)
DIRECT_MODEL_WRITE = re.compile(r"\.save\s*\(|\.objects\.get\s*\(")


def find_violations(root):
    """Return source locations that break the explicit rules in AGENTS.md."""
    violations = []
    for path in sorted((root / "static").rglob("*.css")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PHYSICAL_CSS.search(line):
                violations.append(
                    f"{path.relative_to(root)}:{number}: use logical CSS properties"
                )

    for path in sorted((root / "apps").rglob("*.py")):
        is_view = path.name == "views.py" or "views" in path.relative_to(root).parts
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "csrf_exempt" in line:
                violations.append(
                    f"{path.relative_to(root)}:{number}: CSRF exemptions are forbidden"
                )
            if is_view and DIRECT_MODEL_WRITE.search(line):
                violations.append(
                    f"{path.relative_to(root)}:{number}: use services/scoped lookups"
                )
    return violations


if __name__ == "__main__":
    problems = find_violations(Path(__file__).resolve().parent.parent)
    for problem in problems:
        print(problem)
    if not problems:
        print("CSS and view conventions passed.")
    raise SystemExit(bool(problems))
