from django import forms
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero

class MovimientoManualForm(forms.ModelForm):
    class Meta:
        model = MovimientoFinanciero
        fields = ["fecha", "tipo", "categoria", "centro_costo", "descripcion", "monto", "referencia", "archivo_respaldo", "observaciones"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}), "monto": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = CategoriaFinanciera.objects.filter(activo=True, permite_manual=True).order_by("orden", "codigo")
        self.fields["tipo"].choices = [(choice, label) for choice, label in MovimientoFinanciero.Tipo.choices]

class AnularMovimientoManualForm(forms.Form):
    motivo = forms.CharField(min_length=3, widget=forms.Textarea(attrs={"rows": 3}))


class FiltroMovimientosFinancierosForm(forms.Form):
    fecha_desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    fecha_hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    tipo = forms.ChoiceField(required=False, choices=[("", "Todos")] + list(MovimientoFinanciero.Tipo.choices))
    origen = forms.ChoiceField(required=False, choices=[("", "Todos")] + list(MovimientoFinanciero.Origen.choices))
    categoria = forms.ModelChoiceField(required=False, queryset=CategoriaFinanciera.objects.filter(activo=True))
    estado = forms.ChoiceField(required=False, choices=[("", "Vigentes"), ("ANULADO", "Anulados"), ("TODOS", "Todos")])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fecha_desde") and cleaned.get("fecha_hasta") and cleaned["fecha_desde"] > cleaned["fecha_hasta"]:
            raise forms.ValidationError("La fecha desde no puede ser posterior a la fecha hasta.")
        return cleaned
