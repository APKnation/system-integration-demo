from django.urls import path

from . import views

urlpatterns = [
    path("patients/", views.PatientListCreateView.as_view(), name="hms-patients"),
    path(
        "lab-requests/",
        views.LabRequestListCreateView.as_view(),
        name="hms-lab-requests",
    ),
    path(
        "lab-requests/<uuid:request_id>/result/",
        views.LabRequestResultView.as_view(),
        name="hms-lab-request-result",
    ),
]
