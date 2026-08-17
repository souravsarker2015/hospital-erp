from django.urls import path

from apps.pharmacy import views

app_name = "pharmacy"

urlpatterns = [
    path("", views.DrugListView.as_view(), name="drug_list"),
    path("drugs/new/", views.DrugCreateView.as_view(), name="drug_create"),
    path("drugs/<uuid:pk>/", views.DrugDetailView.as_view(), name="drug_detail"),
    path("drugs/<uuid:pk>/edit/", views.DrugUpdateView.as_view(), name="drug_update"),
    path("drugs/<uuid:pk>/stock-in/", views.StockInView.as_view(), name="stock_in"),
    path("batches/<uuid:pk>/adjust/", views.StockAdjustmentView.as_view(), name="stock_adjust"),
    path("batches-for-drug/", views.BatchesForDrugView.as_view(), name="batches_for_drug"),
    path("dispense/", views.DispenseQueueView.as_view(), name="dispense_queue"),
    path("dispense/<uuid:item_pk>/", views.DispenseView.as_view(), name="dispense"),
]
