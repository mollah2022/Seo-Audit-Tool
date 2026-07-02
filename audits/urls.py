from django.urls import path

from . import views

app_name = "audits"

urlpatterns = [
    path("", views.home, name="home"),
    path("history/", views.audit_history, name="history"),
    path("results/<int:pk>/", views.audit_detail, name="audit_detail"),
    path("history/<int:pk>/delete/", views.delete_audit, name="delete_audit"),
]
