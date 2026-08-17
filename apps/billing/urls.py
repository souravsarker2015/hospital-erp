from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path("", views.InvoiceListView.as_view(), name="invoice_list"),
    path("queue/", views.BillingQueueView.as_view(), name="queue"),
    path("generate/<uuid:appointment_pk>/", views.GenerateInvoiceView.as_view(), name="generate"),
    path("services/", views.ServiceItemListView.as_view(), name="service_list"),
    path("services/new/", views.ServiceItemCreateView.as_view(), name="service_create"),
    path("services/<uuid:pk>/edit/", views.ServiceItemUpdateView.as_view(), name="service_update"),
    path("<uuid:pk>/", views.InvoiceDetailView.as_view(), name="detail"),
    path("<uuid:pk>/print/", views.InvoicePrintView.as_view(), name="print"),
    path("<uuid:pk>/line-items/add/", views.AddLineItemView.as_view(), name="add_line_item"),
    path("<uuid:pk>/payments/record/", views.RecordPaymentView.as_view(), name="record_payment"),
]
