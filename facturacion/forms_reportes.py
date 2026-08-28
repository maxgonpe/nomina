from django import forms

from core.models import CentroCosto
from facturacion.models import CategoriaCompra, Proveedor, DocumentoCompra


class FiltroComprasForm(forms.Form):
    anio = forms.IntegerField(required=False, min_value=2000)
    mes = forms.IntegerField(required=False, min_value=1, max_value=12)
    fecha_desde = forms.DateField(required=False, input_formats=["%Y-%m-%d"], widget=forms.DateInput(attrs={"type": "date"}))
    fecha_hasta = forms.DateField(required=False, input_formats=["%Y-%m-%d"], widget=forms.DateInput(attrs={"type": "date"}))
    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.filter(activo=True), required=False)
    categoria_compra = forms.ModelChoiceField(queryset=CategoriaCompra.objects.filter(activa=True), required=False)
    centro_costo = forms.ModelChoiceField(queryset=CentroCosto.objects.filter(activo=True), required=False)
    tipo_documento = forms.ChoiceField(choices=[], required=False)
    estado = forms.ChoiceField(choices=[("", "Todos")] + list(DocumentoCompra.Estado.choices), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipos = DocumentoCompra.objects.values_list("tipo_documento", flat=True).distinct().order_by("tipo_documento")
        self.fields["tipo_documento"].choices = [("", "Todos")] + [(tipo, tipo) for tipo in tipos]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fecha_desde") and cleaned.get("fecha_hasta") and cleaned["fecha_desde"] > cleaned["fecha_hasta"]:
            raise forms.ValidationError("La fecha desde no puede ser posterior a la fecha hasta.")
        if cleaned.get("anio") and cleaned.get("mes"):
            from datetime import date
            import calendar
            cleaned["fecha_desde"] = date(cleaned["anio"], cleaned["mes"], 1)
            cleaned["fecha_hasta"] = date(cleaned["anio"], cleaned["mes"], calendar.monthrange(cleaned["anio"], cleaned["mes"])[1])
        elif cleaned.get("anio"):
            from datetime import date
            cleaned["fecha_desde"] = date(cleaned["anio"], 1, 1)
            cleaned["fecha_hasta"] = date(cleaned["anio"], 12, 31)
        return cleaned
