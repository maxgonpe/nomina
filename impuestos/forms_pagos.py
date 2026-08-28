from django import forms
from impuestos.models import PagoImpuesto

class PagoImpuestoForm(forms.ModelForm):
    class Meta:
        model = PagoImpuesto
        fields = ["fecha", "monto", "medio_pago", "referencia", "comprobante", "observaciones"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}), "monto": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"})}

class AnularPagoImpuestoForm(forms.Form):
    motivo = forms.CharField(min_length=3, widget=forms.Textarea(attrs={"rows": 3}))
