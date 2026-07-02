from django.http import HttpResponse
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AuditURLForm
from .models import Audit
from .services.orchestrator import run_audit


def home(request):
    if request.method == "POST":
        form = AuditURLForm(request.POST)
        if form.is_valid():
            audit = Audit.objects.create(url=form.cleaned_data["url"])
            run_audit(audit)  # synchronous for v1 — see services/crawler.py

            if audit.status == Audit.Status.FAILED:
                form.add_error(
                    "url",
                    f"We couldn't scan that site: {audit.error_message or 'an unknown error occurred.'}",
                )
            else:
                return redirect("audits:audit_detail", pk=audit.pk)
    else:
        form = AuditURLForm()

    context = {"page_title": "SEO Audit Tool", "form": form}
    return render(request, "audits/home.html", context)


def audit_history(request):
    filter_choice = request.GET.get("filter")
    audits = Audit.objects.all()

    if filter_choice == "good":
        audits = audits.filter(score_band=Audit.ScoreBand.GOOD)
    elif filter_choice == "bad":
        audits = audits.exclude(score_band=Audit.ScoreBand.GOOD)

    paginator = Paginator(audits, 10)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    context = {
        "page_title": "Audit History",
        "audits": page_obj.object_list,
        "filter_choice": filter_choice,
        "page_obj": page_obj,
        "paginator": paginator,
    }
    return render(request, "audits/history.html", context)


def delete_audit(request, pk):
    audit = get_object_or_404(Audit, pk=pk)
    if request.method == "POST":
        audit.delete()
    return redirect("audits:history")


def audit_detail(request, pk):
    audit = get_object_or_404(Audit, pk=pk)

    if not audit.has_saved_result():
        context = {
            "page_title": f"Results unavailable for {audit.domain or audit.url}",
            "audit": audit,
            "error": "This saved audit report is unavailable. It may have been deleted, never finished, or stored incorrectly.",
        }
        return render(request, "audits/audit_detail.html", context)

    context = {
        "page_title": f"Results for {audit.domain or audit.url}",
        "audit": audit,
        "categories": audit.result_categories(),
        "summary": audit.result_summary(),
    }
    return render(request, "audits/audit_detail.html", context)


def audit_pdf(request, pk):
    audit = get_object_or_404(Audit, pk=pk)
    pdf_bytes = build_pdf_response(audit)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="seo-audit-{audit.pk}.pdf"'
    return response


def build_pdf_response(audit):
    lines = [
        "SEO Audit Report",
        "",
        f"Website: {audit.domain or audit.url}",
        f"URL: {audit.url}",
        f"Scanned: {audit.created_at.strftime('%Y-%m-%d %H:%M') if audit.created_at else '-'}",
        f"Status: {audit.get_status_display()}",
        f"Score: {audit.overall_score if audit.overall_score is not None else 'N/A'}",
        f"Label: {audit.score_label or '-'}",
        "",
        "Summary:",
        f"- Total checks: {audit.result_summary().get('total', 0)}",
        f"- Passing: {audit.result_summary().get('pass', 0)}",
        f"- Warnings: {audit.result_summary().get('warn', 0)}",
        f"- Failing: {audit.result_summary().get('fail', 0)}",
        "",
        "Checks by category:",
    ]

    for category in audit.result_categories():
        lines.append(f"- {category.get('name', '')} ({category.get('passing', 0)}/{category.get('total', 0)} passing)")
        for check in category.get("checks", []):
            lines.append(f"  * {check.get('name', '')} [{check.get('status', '')}]")

    return build_simple_pdf(lines)


def build_simple_pdf(lines):
    def escape_pdf_text(text):
        text = str(text or "")
        text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return "".join(ch if ord(ch) < 128 else "?" for ch in text)

    content_lines = []
    y_position = 760
    for line in lines:
        content_lines.append(f"BT /F1 12 Tf 72 {y_position} Td ({escape_pdf_text(line)}) Tj ET")
        y_position -= 14

    content_stream = "\n".join(content_lines)
    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(content_stream.encode('latin-1'))} >>\nstream\n{content_stream}\nendstream\nendobj\n",
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    pdf_bytes = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(obj.encode("latin-1"))

    xref_offset = len(pdf_bytes)
    pdf_bytes.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_bytes.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf_bytes.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    return bytes(pdf_bytes)
