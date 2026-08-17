from django import forms

from apps.billing.models import Payment, ServiceItem


class ServiceItemForm(forms.ModelForm):
    class Meta:
        model = ServiceItem
        fields = ["name", "category", "price"]


class AddLineItemForm(forms.Form):
    service_item = forms.ModelChoiceField(queryset=ServiceItem.objects.none())
    quantity = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, hospital=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_item"].queryset = ServiceItem.objects.filter(hospital=hospital, is_active=True)


class RecordPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["method", "amount", "reference"]
