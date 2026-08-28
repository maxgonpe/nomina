from django import forms

from impuestos.models import PeriodoImpuesto
from impuestos.forms_pagos import PagoImpuestoForm, AnularPagoImpuestoForm


class PeriodoImpuestoForm(forms.ModelForm):
    class Meta:
        model = PeriodoImpuesto
        fields = ["anio", "mes", "observaciones"]
        widgets = {"anio": forms.NumberInput(attrs={"class": "form-control"}), "mes": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 12}), "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3})}

    def clean_mes(self):
        mes = self.cleaned_data["mes"]
        if not 1 <= mes <= 12:
            raise forms.ValidationError("El mes debe estar entre 1 y 12.")
        return mes
