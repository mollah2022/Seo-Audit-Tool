from django.test import TestCase
from django.urls import reverse

from .models import Audit


class AuditHistoryAndPdfTests(TestCase):
    def setUp(self):
        self.audit = Audit.objects.create(
            url="https://example.com",
            domain="example.com",
            status=Audit.Status.DONE,
            overall_score=82,
            score_band=Audit.ScoreBand.GOOD,
            score_label="Strong SEO — foundation",
            result_json={
                "summary": {"total": 2, "pass": 1, "warn": 1, "fail": 0},
                "categories": [
                    {
                        "name": "On-Page",
                        "checks": [{"name": "Meta title — missing", "status": "warn", "detail": "Add a unique title."}],
                    }
                ],
            },
        )

    def test_history_page_lists_saved_audits(self):
        response = self.client.get(reverse("audits:history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Show Results")
        self.assertContains(response, "Delete")
        self.assertContains(response, "example.com")

    def test_pdf_export_downloads_audit_report(self):
        response = self.client.get(reverse("audits:audit_pdf", args=[self.audit.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
