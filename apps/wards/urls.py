from django.urls import path

from apps.wards import views

app_name = "wards"

urlpatterns = [
    path("", views.WardBoardView.as_view(), name="board"),
    path("manage/", views.WardListView.as_view(), name="ward_list"),
    path("manage/new/", views.WardCreateView.as_view(), name="ward_create"),
    path("manage/<uuid:pk>/", views.WardDetailView.as_view(), name="ward_detail"),
    path("manage/<uuid:ward_pk>/rooms/new/", views.RoomCreateView.as_view(), name="room_create"),
    path("rooms/<uuid:pk>/", views.RoomDetailView.as_view(), name="room_detail"),
    path("rooms/<uuid:room_pk>/beds/new/", views.BedCreateView.as_view(), name="bed_create"),
    path("beds/<uuid:pk>/maintenance/", views.ToggleMaintenanceView.as_view(), name="toggle_maintenance"),
    path("admit/<uuid:bed_pk>/", views.AdmitPatientView.as_view(), name="admit"),
    path("admissions/<uuid:pk>/", views.AdmissionDetailView.as_view(), name="admission_detail"),
]
