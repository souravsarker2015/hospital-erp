from django.urls import path

from apps.marketing import views

app_name = "marketing"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
]
