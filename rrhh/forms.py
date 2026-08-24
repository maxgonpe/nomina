from django import forms
from django.core.exceptions import ValidationError

from core.validators import normalizar_rut, validar_rut
from rrhh.models import Trabajador


class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = [
            "rut",
            "nombre_completo",
            "activo",
            "observaciones",
        ]
        widgets = {
            "rut": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "12.345.678-9",
                    "autocomplete": "off",
                }
            ),
            "nombre_completo": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "activo": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def clean_rut(self):
        rut = self.cleaned_data["rut"]
        validar_rut(rut)
        normalizado = normalizar_rut(rut)
        qs = Trabajador.objects.filter(rut_normalizado=normalizado)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un trabajador con este RUT.")
        return rut

    def clean_nombre_completo(self):
        nombre = (self.cleaned_data.get("nombre_completo") or "").strip()
        if not nombre:
            raise ValidationError("El nombre completo es obligatorio.")
        return nombre
