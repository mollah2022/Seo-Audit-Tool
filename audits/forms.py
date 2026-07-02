import ipaddress
import socket
from urllib.parse import urlparse

from django import forms


class AuditURLForm(forms.Form):
    """
    Accepts either a bare domain ("example.com") or a full URL
    ("https://example.com/page") and normalizes it down to a scheme+host
    we can safely hand to the crawler. Includes a basic SSRF guard so the
    audit tool can't be pointed at internal/private infrastructure.
    """

    url = forms.CharField(
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "placeholder": "yourwebsite.com",
                "autocomplete": "off",
                "class": "scan-input",
                "id": "url-input",
            }
        ),
    )

    BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0", "metadata.google.internal"}

    def clean_url(self):
        raw = self.cleaned_data["url"].strip()
        if not raw:
            raise forms.ValidationError("Please enter a URL.")

        if not raw.startswith(("http://", "https://")):
            raw = f"https://{raw}"

        parsed = urlparse(raw)
        hostname = parsed.hostname

        if not hostname or "." not in hostname:
            raise forms.ValidationError("Please enter a valid website URL, e.g. example.com")

        if parsed.scheme not in ("http", "https"):
            raise forms.ValidationError("Only http and https URLs are supported.")

        self._reject_unsafe_hosts(hostname)

        normalized = f"{parsed.scheme}://{hostname}"
        if parsed.port:
            normalized += f":{parsed.port}"
        return normalized

    def _reject_unsafe_hosts(self, hostname):
        """Basic SSRF guard: reject localhost/private/loopback/link-local targets."""
        if hostname.lower() in self.BLOCKED_HOSTNAMES:
            raise forms.ValidationError("That host isn't allowed.")

        try:
            resolved_ips = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
        except socket.gaierror:
            # Can't resolve right now — let the crawler surface a clearer
            # network error later rather than failing validation here.
            return

        for ip in resolved_ips:
            try:
                ip_obj = ipaddress.ip_address(ip)
            except ValueError:
                continue
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                raise forms.ValidationError("That host isn't allowed.")
