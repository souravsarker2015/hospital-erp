from django import forms

from apps.patients.models import Patient
from apps.users.models import User
from apps.wards.models import Bed, Room, Ward


class WardForm(forms.ModelForm):
    class Meta:
        model = Ward
        fields = ["name", "ward_type"]


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["room_number"]


class BedForm(forms.ModelForm):
    class Meta:
        model = Bed
        fields = ["bed_number", "daily_rate"]


class AdmitPatientForm(forms.Form):
    patient_id = forms.UUIDField(widget=forms.HiddenInput)
    admitting_doctor = forms.ModelChoiceField(queryset=User.objects.none())
    reason = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"placeholder": "e.g. Acute appendicitis, observation"}))

    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hospital = hospital
        self.fields["admitting_doctor"].queryset = User.objects.filter(hospital=hospital, role=User.Role.DOCTOR, is_active=True)

    def clean_patient_id(self):
        patient_id = self.cleaned_data["patient_id"]
        try:
            return Patient.objects.get(pk=patient_id, hospital=self.hospital)
        except Patient.DoesNotExist:
            raise forms.ValidationError("Select a patient from the search results.")


class DischargeForm(forms.Form):
    discharge_summary = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Diagnosis, treatment given, condition at discharge, follow-up instructions"})
    )
