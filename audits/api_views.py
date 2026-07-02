"""
Audit History API.

Plain Django JSON views (no DRF dependency) covering:
    POST   /api/audits/        save a new audit (runs it synchronously, then stores it)
    GET    /api/audits/        list audit history, newest first
    GET    /api/audits/<id>/   fetch a single saved audit, including its full result JSON
    DELETE /api/audits/<id>/   remove an audit from history

These are @csrf_exempt because they're meant to be called as a plain JSON
API (e.g. from a JS frontend or an external client) rather than from a
browser-submitted HTML form. If this API is ever exposed publicly, put it
behind authentication/rate limiting.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .forms import AuditURLForm
from .models import Audit
from .services.orchestrator import run_audit


def _parse_json_body(request):
    """Returns the parsed JSON body, {} for an empty body, or None if the
    body isn't valid JSON."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _get_audit_or_404(pk):
    try:
        return Audit.objects.get(pk=pk)
    except Audit.DoesNotExist:
        return None


@csrf_exempt
@require_http_methods(["GET", "POST"])
def audit_list_create(request):
    """GET: list audit history. POST: run + save a new audit."""
    if request.method == "GET":
        return _list_audits(request)
    return _create_audit(request)


def _list_audits(request):
    # Audit.Meta.ordering = ["-created_at"], so this is already newest-first.
    queryset = Audit.objects.all()

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    limit_param = request.GET.get("limit")
    if limit_param:
        try:
            limit = max(0, int(limit_param))
            queryset = queryset[:limit]
        except ValueError:
            return JsonResponse({"error": "limit must be an integer."}, status=400)

    results = [audit.to_summary_dict() for audit in queryset]
    return JsonResponse({"count": len(results), "results": results})


def _create_audit(request):
    payload = _parse_json_body(request)
    if payload is None:
        return JsonResponse({"error": "Request body must be valid JSON."}, status=400)

    form = AuditURLForm({"url": payload.get("url", "")})
    if not form.is_valid():
        message = next(iter(form.errors.get("url", [])), "Invalid URL.")
        return JsonResponse({"error": message}, status=400)

    audit = Audit.objects.create(url=form.cleaned_data["url"])
    run_audit(audit)  # synchronous for v1 — see services/crawler.py

    if audit.status == Audit.Status.FAILED:
        return JsonResponse(
            {
                "error": audit.error_message or "The audit failed.",
                "audit": audit.to_detail_dict(),
            },
            status=422,
        )

    return JsonResponse(audit.to_detail_dict(), status=201)


@csrf_exempt
@require_http_methods(["GET", "DELETE"])
def audit_detail_delete(request, pk):
    """GET: fetch one saved audit (full JSON). DELETE: remove it from history."""
    audit = _get_audit_or_404(pk)
    if audit is None:
        return JsonResponse({"error": "Audit not found."}, status=404)

    if request.method == "DELETE":
        audit_id = audit.pk
        audit.delete()
        return JsonResponse({"deleted": True, "id": audit_id})

    return JsonResponse(audit.to_detail_dict())