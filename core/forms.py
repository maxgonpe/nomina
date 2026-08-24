from django import forms
from django.core.exceptions import ValidationError

from core.models import ParametroNegocio, ParametroValor


class ParametroNegocioForm(forms.ModelForm):
    class Meta:
        model = ParametroNegocio
        fields = ["codigo", "nombre", "descripcion", "activo"]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "activo": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["codigo"].disabled = True

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not codigo:
            raise ValidationError("El código es obligatorio.")
        qs = ParametroNegocio.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un parámetro con este código.")
        return codigo

    def validate_unique(self):
        exclude = set(self._get_validation_exclusions())
        exclude.add("codigo")
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as exc:
            self._update_errors(exc)


class ParametroValorForm(forms.ModelForm):
    class Meta:
        model = ParametroValor
        fields = [
            "valor",
            "vigencia_desde",
            "vigencia_hasta",
            "observaciones",
        ]
        widgets = {
            "valor": forms.NumberInput(
                attrs={"class": "form-control", "step": "any"}
            ),
            "vigencia_desde": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "vigencia_hasta": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vigencia_desde"].input_formats = ["%Y-%m-%d"]
        self.fields["vigencia_hasta"].input_formats = ["%Y-%m-%d"]
        self.fields["vigencia_hasta"].required = False
