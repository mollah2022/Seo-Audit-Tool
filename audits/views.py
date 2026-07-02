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
    audits = Audit.objects.all()
    return render(request, "audits/history.html", {"page_title": "Audit History", "audits": audits})


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
