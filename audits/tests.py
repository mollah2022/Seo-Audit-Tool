from django.test import TestCase
from django.urls import reverse

from .models import Audit
from .services.scoring import compute_overall_score


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

    def test_compute_overall_score_counts_warnings_as_partial_credit(self):
        checks = [
            {"status": "pass"} for _ in range(8)
        ] + [
            {"status": "warn"} for _ in range(10)
        ] + [
            {"status": "fail"} for _ in range(3)
        ]

        self.assertEqual(compute_overall_score(checks), 81)

    def test_history_page_filter_buttons(self):
        Audit.objects.create(
            url="https://good.example.com",
            domain="good.example.com",
            status=Audit.Status.DONE,
            overall_score=90,
            score_band=Audit.ScoreBand.GOOD,
            score_label="Good",
            result_json={"summary": {"total": 1, "pass": 1, "warn": 0, "fail": 0}, "categories": []},
        )
        Audit.objects.create(
            url="https://bad.example.com",
            domain="bad.example.com",
            status=Audit.Status.DONE,
            overall_score=40,
            score_band=Audit.ScoreBand.WARN,
            score_label="Needs work",
            result_json={"summary": {"total": 1, "pass": 0, "warn": 1, "fail": 0}, "categories": []},
        )

        response = self.client.get(reverse("audits:history") + "?filter=good")
        self.assertContains(response, "good.example.com")
        self.assertNotContains(response, "bad.example.com")

        response = self.client.get(reverse("audits:history") + "?filter=bad")
        self.assertContains(response, "bad.example.com")
        self.assertNotContains(response, "good.example.com")

    def test_history_page_paginates_results(self):
        for i in range(15):
            Audit.objects.create(
                url=f"https://site{i}.example.com",
                domain=f"site{i}.example.com",
                status=Audit.Status.DONE,
                overall_score=50,
                score_band=Audit.ScoreBand.WARN,
                score_label="Needs work",
                result_json={"summary": {"total": 1, "pass": 0, "warn": 1, "fail": 0}, "categories": []},
            )

        response = self.client.get(reverse("audits:history") + "?page=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 1 of 2")

        response = self.client.get(reverse("audits:history") + "?page=2")
        self.assertContains(response, "Page 2 of 2")
