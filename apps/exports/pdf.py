"""Render dedicated print templates with local static assets; never persist files."""

from pathlib import Path

from django.contrib.staticfiles import finders
from django.template.loader import render_to_string


def render_pdf(template, context):
    """Resolve source assets in tests and the image, without an HTTP font request."""
    from weasyprint import CSS, HTML
    from weasyprint.text.fonts import FontConfiguration

    fonts = FontConfiguration()
    stylesheet = Path(finders.find("css/pdf.css"))
    html = render_to_string(template, context)
    return HTML(string=html, base_url=stylesheet.parent.as_uri()).write_pdf(
        stylesheets=[CSS(filename=str(stylesheet), font_config=fonts)],
        font_config=fonts,
    )
