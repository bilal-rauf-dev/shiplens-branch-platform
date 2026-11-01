"""Local documentation links must point to files or directories in the checkout."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown
import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]


class DocumentationLinks(HTMLParser):
    """Collect link and image attributes while ignoring code examples."""

    def __init__(self):
        super().__init__()
        self.targets = []
        self.code_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"pre", "code"}:
            self.code_depth += 1
        if self.code_depth:
            return
        for name, value in attrs:
            if name in {"src", "href"} and value:
                self.targets.append(value)

    def handle_endtag(self, tag):
        if tag in {"pre", "code"} and self.code_depth:
            self.code_depth -= 1


def relative_targets(source):
    """Render Markdown so images, reference links and escaped code parse correctly."""
    parser = DocumentationLinks()
    parser.feed(markdown.markdown(source, extensions=["fenced_code"]))
    targets = []
    for target in parser.targets:
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        targets.append(unquote(url.path))
    return targets


@pytest.mark.parametrize(
    "document", DOCUMENTS, ids=lambda path: path.relative_to(ROOT).as_posix()
)
def test_doc_links(document):
    targets = relative_targets(document.read_text(encoding="utf-8"))
    missing = [target for target in targets if not (document.parent / target).exists()]
    assert not missing, "Missing documentation targets:\n" + "\n".join(missing)


def test_doc_link_collection_handles_markup_and_ignores_examples():
    source = """
[guide](guide.md#intro) ![image](images/example.svg)
[reference][local]
[![badge](images/badge.svg)](../README.md)
<img src="images/with%20space.png"><a href='notes.md#next'>notes</a>
<a href="notes.md?view=source#next">notes</a>
[web](https://example.com/missing) [http](http://example.com/missing)
[email](mailto:help@example.com) [anchor](#intro)
<img src="https://example.com/image.png">
`[example](missing-inline.md)` ``<img src="missing-inline.png">``
<code><a href="missing-code.md">example</a></code>

```markdown
[example](missing-fenced.md)
<img src="missing-fenced.png">
```

~~~html
<a href="missing-tilde.md">example</a>
~~~

[local]: reference.md "Reference title"
"""
    assert relative_targets(source) == [
        "guide.md",
        "images/example.svg",
        "reference.md",
        "../README.md",
        "images/badge.svg",
        "images/with space.png",
        "notes.md",
        "notes.md",
    ]
