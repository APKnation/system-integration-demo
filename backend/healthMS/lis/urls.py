from django.urls import path

from . import views

urlpatterns = [
    path(
        "orders/",
        views.LabOrderIngestView.as_view(),
        name="lis-order-ingest",
    ),
    path(
        "orders/<uuid:request_id>/",
        views.LabOrderStatusView.as_view(),
        name="lis-order-status",
    ),
    path(
        "orders/<uuid:request_id>/result/",
        views.LabResultView.as_view(),
        name="lis-order-result",
    ),
    path(
        "orders/<uuid:request_id>/process/",
        views.LabOrderProcessView.as_view(),
        name="lis-order-process",
    ),
    path(
        "orders/<uuid:request_id>/status/",
        views.LabOrderStatusUpdateView.as_view(),
        name="lis-order-status-update",
    ),
    path(
        "catalog/",
        views.LabTestCatalogView.as_view(),
        name="lis-catalog",
    ),
]
