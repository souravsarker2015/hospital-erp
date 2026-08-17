from django import forms
from django.urls import reverse

from apps.pharmacy.models import Drug, StockBatch


class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = ["name", "generic_name", "strength", "unit", "low_stock_threshold", "unit_price"]


class StockInForm(forms.ModelForm):
    class Meta:
        model = StockBatch
        fields = ["batch_number", "expiry_date", "quantity_received", "supplier"]
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {"quantity_received": "Quantity"}


class DispenseForm(forms.Form):
    drug = forms.ModelChoiceField(queryset=Drug.objects.none())
    batch = forms.ModelChoiceField(queryset=StockBatch.objects.none(), required=False)
    quantity = forms.IntegerField(min_value=1)

    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.hospital = hospital
        self.fields["drug"].queryset = Drug.objects.filter(hospital=hospital, is_active=True)
        # The batch <select> is repopulated client-side by the htmx-driven
        # _batch_field.html partial once a drug is chosen, but the form
        # field itself still needs a queryset covering whatever gets
        # submitted, or a legitimately-selected batch fails validation as
        # "not a valid choice".
        self.fields["batch"].queryset = StockBatch.objects.filter(hospital=hospital, quantity_remaining__gt=0)
        batch_refresh = {
            "hx-get": reverse("pharmacy:batches_for_drug"),
            "hx-trigger": "change",
            "hx-target": "#batch-field",
            "hx-swap": "outerHTML",
        }
        self.fields["drug"].widget.attrs.update(batch_refresh)

    def clean(self):
        cleaned_data = super().clean()
        drug = cleaned_data.get("drug")
        batch = cleaned_data.get("batch")
        quantity = cleaned_data.get("quantity")
        if not batch and drug:
            self.add_error("batch", "Select a batch to dispense from.")
        elif batch and drug and batch.drug_id != drug.id:
            self.add_error("batch", "That batch doesn't belong to the selected drug.")
        elif batch and quantity and quantity > batch.quantity_remaining:
            self.add_error("quantity", f"Only {batch.quantity_remaining} left in this batch.")
        return cleaned_data


class StockAdjustmentForm(forms.Form):
    quantity_delta = forms.IntegerField(
        label="Adjustment", help_text="Negative to remove stock (e.g. damaged), positive to add."
    )
    notes = forms.CharField(max_length=255, widget=forms.TextInput(attrs={"placeholder": "Reason for adjustment"}))
