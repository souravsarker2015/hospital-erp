from django import forms

from apps.patients.models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "phone_number",
            "email",
            "address",
            "blood_group",
            "allergies",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 2}),
            "allergies": forms.Textarea(
                attrs={"rows": 2, "placeholder": "e.g. Penicillin, Peanuts"}
            ),
        }
