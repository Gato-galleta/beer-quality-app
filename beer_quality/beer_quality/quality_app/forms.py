from django import forms
from .models import QualityParameter

class QualityParameterForm(forms.ModelForm):
    class Meta:
        model = QualityParameter
        fields = ['temperature', 'ph', 'alcohol']
