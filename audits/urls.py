from django.urls import path

from . import views

app_name = "audits"

urlpatterns = [
    path("", views.home, name="home"),
    path("results/<int:pk>/", views.audit_detail, name="audit_detail"),
]
