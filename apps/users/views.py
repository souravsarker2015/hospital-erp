from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy

from apps.users.forms import LoginForm


class LoginView(DjangoLoginView):
    template_name = "users/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if self.request.hospital is not None and user.hospital_id != self.request.hospital.id:
            form.add_error(
                None, ValidationError("This account does not belong to this hospital.")
            )
            return self.form_invalid(form)
        return super().form_valid(form)


class LogoutView(DjangoLogoutView):
    pass


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "users/password_reset_form.html"
    email_template_name = "users/password_reset_email.html"
    subject_template_name = "users/password_reset_subject.txt"
    success_url = reverse_lazy("users:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "users/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "users/password_reset_complete.html"
