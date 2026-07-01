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
