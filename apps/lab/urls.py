from django.urls import path

from apps.lab import views

app_name = "lab"

urlpatterns = [
    path("", views.LabTestListView.as_view(), name="test_list"),
    path("tests/new/", views.LabTestCreateView.as_view(), name="test_create"),
    path("tests/<uuid:pk>/edit/", views.LabTestUpdateView.as_view(), name="test_update"),
    path("queue/", views.LabQueueView.as_view(), name="queue"),
    path("orders/<uuid:order_pk>/collect/", views.CollectSampleView.as_view(), name="collect_sample"),
    path("orders/<uuid:order_pk>/result/", views.EnterResultView.as_view(), name="enter_result"),
    path("orders/<uuid:order_pk>/report/", views.LabReportPDFView.as_view(), name="report_pdf"),
]
