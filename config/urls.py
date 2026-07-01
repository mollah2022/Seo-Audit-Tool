"""
Root URL configuration for the SEO Audit Tool project.

App-specific routes live in each app's own urls.py and are wired in here
with include(), keeping this file as a simple top-level router.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("audits.urls")),
]

# Serve user-uploaded media (e.g. Playwright screenshots) locally in DEBUG.
# In production this should be handled by the web server / a storage service.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
