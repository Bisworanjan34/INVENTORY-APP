from django import forms
from .models import Bill


class BillUploadForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ["bill_image"]  # Employee sirf photo upload karega
