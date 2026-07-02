from django.db import models
from django.urls import reverse


class Audit(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    class ScoreBand(models.TextChoices):
        GOOD = "good", "Good"
        WARN = "warn", "Needs work"
        POOR = "poor", "Poor"

    url = models.URLField(max_length=500)
    domain = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    overall_score = models.IntegerField(null=True, blank=True)
    score_band = models.CharField(max_length=10, choices=ScoreBand.choices, blank=True)
    score_label = models.CharField(max_length=150, blank=True)
    error_message = models.TextField(blank=True)
    # Full snapshot of the audit result (categories, checks, summary) at the
    # moment the audit finished, so audit history can be served — and later
    # re-displayed or exported — without re-joining CheckResult rows.
    result_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.domain or self.url} ({self.status})"

    def get_absolute_url(self):
        return reverse("audits:audit_detail", args=[self.pk])

    # Channel letters (A-E) are cosmetic labels shown on the report page.
    CATEGORY_ORDER = (
        ("on_page", "A", "On-Page"),
        ("technical", "B", "Technical"),
        ("social", "C", "Social Metadata"),
        ("links", "D", "Links"),
        ("performance", "E", "Performance"),
    )

    def checks_by_category(self):
        all_checks = list(self.checks.all())
        grouped = []
        for key, channel, label in self.CATEGORY_ORDER:
            checks = [c for c in all_checks if c.category == key]
            if not checks:
                continue
            passing = sum(1 for c in checks if c.status == CheckResult.Status.PASS)
            grouped.append(
                {
                    "channel": channel,
                    "name": label,
                    "checks": checks,
                    "passing": passing,
                    "total": len(checks),
                }
            )
        return grouped

    def summary(self):
        """
        Aggregate pass/warn/fail counts (and their share of the total, as a
        percentage) across every check, used to drive the results page's
        segmented signal bar.
        """
        all_checks = list(self.checks.all())
        total = len(all_checks)
        counts = {status: 0 for status, _ in CheckResult.Status.choices}
        for check in all_checks:
            counts[check.status] = counts.get(check.status, 0) + 1

        def pct(count):
            return round((count / total) * 100) if total else 0

        return {
            "total": total,
            "pass": counts.get(CheckResult.Status.PASS, 0),
            "warn": counts.get(CheckResult.Status.WARN, 0),
            "fail": counts.get(CheckResult.Status.FAIL, 0),
            "pass_pct": pct(counts.get(CheckResult.Status.PASS, 0)),
            "warn_pct": pct(counts.get(CheckResult.Status.WARN, 0)),
            "fail_pct": pct(counts.get(CheckResult.Status.FAIL, 0)),
        }

    def has_saved_result(self):
        return bool(self.result_json and self.result_json.get("categories"))

    def result_categories(self):
        return self.result_json.get("categories", []) if self.result_json else []

    def result_summary(self):
        if not self.result_json:
            return {"total": 0, "pass": 0, "warn": 0, "fail": 0, "pass_pct": 0, "warn_pct": 0, "fail_pct": 0}

        summary = self.result_json.get("summary", {})
        total = summary.get("total", 0)

        def pct(count):
            return round((count / total) * 100) if total else 0

        return {
            "total": total,
            "pass": summary.get("pass", 0),
            "warn": summary.get("warn", 0),
            "fail": summary.get("fail", 0),
            "pass_pct": pct(summary.get("pass", 0)),
            "warn_pct": pct(summary.get("warn", 0)),
            "fail_pct": pct(summary.get("fail", 0)),
        }

    # -- Audit History API serialization --------------------------------
    def to_summary_dict(self):
        """Lightweight representation used by the history list endpoint."""
        return {
            "id": self.pk,
            "url": self.url,
            "domain": self.domain,
            "status": self.status,
            "score": self.overall_score,
            "score_band": self.score_band,
            "score_label": self.score_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_detail_dict(self):
        """Full representation, including the saved JSON result, used by
        the single-audit endpoint and by the save-audit response."""
        data = self.to_summary_dict()
        data["error_message"] = self.error_message
        data["result"] = self.result_json
        return data


class CheckResult(models.Model):
    class Category(models.TextChoices):
        ON_PAGE = "on_page", "On-Page"
        TECHNICAL = "technical", "Technical"
        SOCIAL = "social", "Social Metadata"
        LINKS = "links", "Links"
        PERFORMANCE = "performance", "Performance"

    class Status(models.TextChoices):
        PASS = "pass", "Pass"
        WARN = "warn", "Warning"
        FAIL = "fail", "Fail"

    audit = models.ForeignKey(Audit, related_name="checks", on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=Category.choices)
    name = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=Status.choices)
    detail = models.TextField(blank=True)
    # "How to fix it" — kept separate from `detail` ("what's wrong") so the
    # UI can render them as two distinct, clearly labeled pieces of text.
    recommendation = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"[{self.category}] {self.name}: {self.status}"