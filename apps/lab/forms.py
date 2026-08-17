from django import forms

from apps.lab.models import LabResult, LabTest


class LabTestForm(forms.ModelForm):
    class Meta:
        model = LabTest
        fields = ["name", "code", "sample_type", "unit", "reference_range", "price"]


class CollectSampleForm(forms.Form):
    test = forms.ModelChoiceField(queryset=LabTest.objects.none(), label="Match to catalog test")

    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["test"].queryset = LabTest.objects.filter(hospital=hospital, is_active=True)


class ResultEntryForm(forms.ModelForm):
    class Meta:
        model = LabResult
        fields = ["result_value", "result_notes", "is_abnormal"]
        widgets = {
            "result_notes": forms.Textarea(attrs={"rows": 3}),
        }
