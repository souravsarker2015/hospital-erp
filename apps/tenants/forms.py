from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from apps.tenants.models import Hospital

RESERVED_SUBDOMAINS = {"www", "app", "api", "admin", "static", "media", "mail"}

INPUT_CLASSES = (
    "block w-full rounded-lg border border-brand-900/15 bg-white px-3.5 py-2.5 text-sm "
    "text-brand-950 placeholder:text-brand-900/30 focus:border-brand-500 focus:outline-none "
    "focus:ring-2 focus:ring-brand-500/20"
)


class HospitalSignupForm(forms.Form):
    hospital_name = forms.CharField(
        max_length=200,
        label="Hospital / clinic name",
        widget=forms.TextInput(attrs={"placeholder": "City Care Hospital"}),
    )
    subdomain = forms.SlugField(
        max_length=63,
        label="Subdomain",
        help_text="Your workspace will live at <subdomain>.yourapp.com",
        widget=forms.TextInput(attrs={"placeholder": "citycare"}),
    )
    contact_email = forms.EmailField(
        label="Hospital contact email",
        widget=forms.EmailInput(attrs={"placeholder": "admin@citycare.com"}),
    )
    admin_first_name = forms.CharField(max_length=150, label="Your first name")
    admin_last_name = forms.CharField(max_length=150, label="Your last name")
    admin_username = forms.CharField(max_length=150, label="Choose a username")
    admin_password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    admin_password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT_CLASSES)

    def clean_subdomain(self):
        subdomain = self.cleaned_data["subdomain"].lower()
        if subdomain in RESERVED_SUBDOMAINS:
            raise ValidationError("That subdomain is reserved. Please choose another.")
        if Hospital.objects.filter(subdomain=subdomain).exists():
            raise ValidationError("That subdomain is already taken.")
        return subdomain

    def clean_admin_username(self):
        from apps.users.models import User

        username = self.cleaned_data["admin_username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("That username is already taken. Try another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("admin_password1")
        password2 = cleaned_data.get("admin_password2")
        if password1 and password2 and password1 != password2:
            self.add_error("admin_password2", "Passwords do not match.")
        elif password1:
            try:
                password_validation.validate_password(password1)
            except ValidationError as exc:
                self.add_error("admin_password1", exc)
        return cleaned_data
