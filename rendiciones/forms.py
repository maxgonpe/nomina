from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from rendiciones.models import Rendicion
from rrhh.models import Trabajador


class RendicionForm(forms.ModelForm):
    class Meta:
        model = Rendicion
        fields = [
            "trabajador",
            "fecha",
            "descripcion",
            "total_declarado",
            "observaciones",
        ]
        widgets = {
            "trabajador": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "descripcion": forms.TextInput(attrs={"class": "form-control"}),
            "total_declarado": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.trabajador_id:
            qs = Trabajador.objects.filter(
                Q(activo=True) | Q(pk=self.instance.trabajador_id)
            )
        else:
            qs = Trabajador.objects.filter(activo=True)
        self.fields["trabajador"].queryset = qs.order_by("nombre_completo")
        self.fields["trabajador"].empty_label = "Seleccione trabajador"
        self.fields["fecha"].input_formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
        ]

    def clean_descripcion(self):
        descripcion = (self.cleaned_data.get("descripcion") or "").strip()
        if not descripcion:
            raise ValidationError("La descripción es obligatoria.")
        return descripcion

    def clean_total_declarado(self):
        total = self.cleaned_data.get("total_declarado")
        if total is None:
            raise ValidationError("El total declarado es obligatorio.")
        if total < 0:
            raise ValidationError("El total declarado no puede ser negativo.")
        return total

    def clean_trabajador(self):
        trabajador = self.cleaned_data.get("trabajador")
        if trabajador is None:
            raise ValidationError("Debe indicar un trabajador.")
        if not self.instance.pk and not trabajador.activo:
            raise ValidationError(
                "Solo se pueden crear rendiciones para trabajadores activos."
            )
        if (
            self.instance.pk
            and trabajador.pk != self.instance.trabajador_id
            and not trabajador.activo
        ):
            raise ValidationError(
                "Solo se puede cambiar a un trabajador activo."
            )
        return trabajador
