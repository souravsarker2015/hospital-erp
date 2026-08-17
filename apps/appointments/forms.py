from django import forms
from django.urls import reverse

from apps.appointments.models import DoctorSchedule
from apps.patients.models import Patient
from apps.users.models import User


class DoctorScheduleForm(forms.ModelForm):
    class Meta:
        model = DoctorSchedule
        fields = ["doctor", "weekday", "start_time", "end_time", "slot_duration_minutes"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = User.objects.filter(hospital=hospital, role=User.Role.DOCTOR, is_active=True)


class BookAppointmentForm(forms.Form):
    patient_id = forms.UUIDField(widget=forms.HiddenInput(attrs={"x-bind:value": "selectedPatientId"}))
    doctor = forms.ModelChoiceField(queryset=User.objects.none())
    appointment_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.HiddenInput(attrs={"x-bind:value": "selectedTime"}))
    reason = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={"placeholder": "e.g. Fever, follow-up visit"}))

    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hospital = hospital
        self.fields["doctor"].queryset = User.objects.filter(hospital=hospital, role=User.Role.DOCTOR, is_active=True)
        slot_refresh = {
            "hx-get": reverse("appointments:slots"),
            "hx-trigger": "change",
            "hx-target": "#slot-picker",
            "hx-include": "#doctor-field, #date-field",
        }
        self.fields["doctor"].widget.attrs.update({**slot_refresh, "id": "doctor-field"})
        self.fields["appointment_date"].widget.attrs.update({**slot_refresh, "id": "date-field"})

    def clean_patient_id(self):
        patient_id = self.cleaned_data["patient_id"]
        try:
            return Patient.objects.get(pk=patient_id, hospital=self.hospital)
        except Patient.DoesNotExist:
            raise forms.ValidationError("Select a patient from the search results.")

    def clean_patient_id(self):
        patient_id = self.cleaned_data["patient_id"]
        try:
            return Patient.objects.get(pk=patient_id, hospital=self.hospital)
        except Patient.DoesNotExist:
            raise forms.ValidationError("Select a patient from the search results.")
