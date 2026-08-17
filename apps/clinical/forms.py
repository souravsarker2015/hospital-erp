from django import forms
from django.forms import inlineformset_factory

from apps.clinical.models import Consultation, LabOrder, PrescriptionItem, Vitals


class VitalsForm(forms.ModelForm):
    class Meta:
        model = Vitals
        fields = [
            "temperature_celsius",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "pulse_rate",
            "respiratory_rate",
            "spo2_percent",
            "weight_kg",
            "height_cm",
        ]


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            "chief_complaint",
            "history_notes",
            "examination_notes",
            "diagnosis",
            "icd10_code",
            "advice",
            "follow_up_date",
        ]
        widgets = {
            "history_notes": forms.Textarea(attrs={"rows": 3}),
            "examination_notes": forms.Textarea(attrs={"rows": 3}),
            "diagnosis": forms.Textarea(attrs={"rows": 2}),
            "advice": forms.Textarea(attrs={"rows": 2}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "icd10_code": forms.TextInput(attrs={"placeholder": "e.g. J06.9"}),
        }


PrescriptionItemFormSet = inlineformset_factory(
    Consultation,
    PrescriptionItem,
    fields=["drug_name", "dosage", "frequency", "duration", "instructions"],
    extra=5,
    can_delete=True,
    widgets={
        "drug_name": forms.TextInput(attrs={"placeholder": "Drug name"}),
        "dosage": forms.TextInput(attrs={"placeholder": "500mg"}),
        "frequency": forms.TextInput(attrs={"placeholder": "1-0-1"}),
        "duration": forms.TextInput(attrs={"placeholder": "5 days"}),
        "instructions": forms.TextInput(attrs={"placeholder": "After meals"}),
    },
)

LabOrderFormSet = inlineformset_factory(
    Consultation,
    LabOrder,
    fields=["test_name", "notes"],
    extra=3,
    can_delete=True,
    widgets={
        "test_name": forms.TextInput(attrs={"placeholder": "e.g. Complete Blood Count"}),
        "notes": forms.TextInput(attrs={"placeholder": "e.g. Fasting required"}),
    },
)
