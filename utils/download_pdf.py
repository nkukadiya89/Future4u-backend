from io import BytesIO

from django.http import HttpResponse
from django.template.loader import get_template, render_to_string
from xhtml2pdf import pisa


def render_to_pdf(template_src, context_data):
    if isinstance(context_data, list):
        context_dict = {"data": context_data}
    elif isinstance(context_data, dict):
        context_dict = context_data
    else:
        raise TypeError("context must be a dict or list.")

    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type="application/pdf")
    return None


def email_render_to_pdf(template_src, context_dict={}):
    result = BytesIO()
    pdf = pisa.CreatePDF(render_to_string(template_src, context_dict), dest=result)
    if not pdf.err:
        return result.getvalue()
    return None


def generate_pr_pdf(context):
    html_content = render_to_string("rfq_template.html", context)

    pdf_buffer = BytesIO()

    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer, encoding="utf-8")

    if not pisa_status.err:
        return pdf_buffer.getvalue()
    return None
