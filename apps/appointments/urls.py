from django.urls import path

from apps.appointments import views

app_name = "appointments"

urlpatterns = [
    path("", views.QueueView.as_view(), name="queue"),
    path("book/", views.BookAppointmentView.as_view(), name="book"),
    path("patient-search/", views.PatientSearchView.as_view(), name="patient_search"),
    path("slots/", views.SlotsView.as_view(), name="slots"),
    path("<uuid:pk>/status/", views.AppointmentStatusView.as_view(), name="status"),
    path("schedules/", views.DoctorScheduleListView.as_view(), name="schedules"),
    path("schedules/new/", views.DoctorScheduleCreateView.as_view(), name="schedule_create"),
    path("schedules/<uuid:pk>/delete/", views.DoctorScheduleDeleteView.as_view(), name="schedule_delete"),
]
