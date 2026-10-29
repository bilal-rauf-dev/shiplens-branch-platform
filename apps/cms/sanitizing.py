"""The small Markdown allow-list in BR-123, shared by saves and rendering."""

import markdown
import nh3

TAGS = {"p", "h2", "h3", "h4", "ul", "ol", "li", "a", "strong", "em", "blockquote"}


def sanitize(value):
    return nh3.clean(
        value,
        tags=TAGS,
        attributes={"a": {"href"}},
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener",
    )


def from_markdown(value):
    return sanitize(markdown.markdown(value))
