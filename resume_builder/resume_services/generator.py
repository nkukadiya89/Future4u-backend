"""
PDF generation service.

Flow: resume data → Jinja2 HTML template → xhtml2pdf → PDF bytes
"""

from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path
from urllib.request import pathname2url

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from xhtml2pdf import pisa

from resume_builder.resume_services.config import TEMPLATES_DIR


def _photo_to_uri(path: str) -> str:
    """Convert a local file path to a file:/// URI that xhtml2pdf can load."""
    abs_path = os.path.abspath(path)
    return "file:///" + pathname2url(abs_path).lstrip("/")


def _prepare_context(data: dict) -> dict:
    """Normalise photo path to a file URI so xhtml2pdf renders it."""
    ctx = dict(data)
    pi = ctx.get("personal_info", {})
    if isinstance(pi, dict) and pi.get("photo"):
        pi = dict(pi)
        pi["photo"] = _photo_to_uri(pi["photo"])
        ctx["personal_info"] = pi
    return ctx


def _link_callback(uri: str, rel: str) -> str:
    """
    xhtml2pdf link callback — resolves file:/// URIs back to absolute paths
    so the PDF engine can open them directly.
    """
    if uri.startswith("file:///"):
        path = uri[8:].replace("/", os.sep)
        if os.path.isfile(path):
            return path
    return uri


def _render_html(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
    )
    try:
        template = env.get_template(f"{template_name}.html")
    except TemplateNotFound:
        raise ValueError(f"Template '{template_name}' not found in {TEMPLATES_DIR}")
    return template.render(**context)


def _html_to_pdf(html: str) -> bytes:
    """Convert an HTML string to PDF bytes using xhtml2pdf."""
    buf = BytesIO()
    result = pisa.CreatePDF(html, dest=buf, link_callback=_link_callback)
    if result.err:
        raise RuntimeError(f"PDF generation failed with error code: {result.err}")
    return buf.getvalue()


logger = logging.getLogger(__name__)

# Jinja themes that have a physical template file. The template registry may
# contain many more JSON Resume themes (modern, minimal, academic, elegant,
# compact, stackoverflow, ...) that are rendered by the frontend; for those the
# optional PDF endpoint falls back to the professional layout instead of 500.
_PDF_TEMPLATE_FALLBACK = "professional"


def _available_template_name(template_name: str) -> str:
    """Return the Jinja template file to render, falling back safely.

    Theme codes that only exist in the registry / frontend (no .html file in
    TEMPLATES_DIR) are rendered with the default PDF layout.
    """
    if (TEMPLATES_DIR / f"{template_name}.html").is_file():
        return template_name
    logger.info(
        "Resume PDF fallback: theme '%s' has no Jinja template, using '%s'",
        template_name,
        _PDF_TEMPLATE_FALLBACK,
    )
    return _PDF_TEMPLATE_FALLBACK


def build_resume(data: dict, summary: str) -> bytes:
    """
    Build a PDF resume from structured data and an AI-enhanced summary.

    Args:
        data:    Serialized resume model dict
        summary: AI-enhanced summary/objective text

    Returns:
        PDF file as bytes
    """
    requested = data.get("template", "professional")
    template_name = _available_template_name(requested)
    context = _prepare_context({**data, "template": template_name, "summary": summary})
    html = _render_html(template_name, context)
    return _html_to_pdf(html)
