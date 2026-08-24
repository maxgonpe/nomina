from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from remuneraciones.models import NOMBRE_MES, ConceptoRemuneracion, PeriodoRemuneracion

MES_CHOICES = [(numero, nombre) for numero, nombre in NOMBRE_MES.items()]


class PeriodoForm(forms.ModelForm):
    mes = forms.TypedChoiceField(
        choices=MES_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = PeriodoRemuneracion
        fields = ["anio", "mes", "observaciones"]
        widgets = {
            "anio": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 2000,
                    "max": 2100,
                }
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["anio"].initial = timezone.localdate().year
        else:
            self.fields["anio"].disabled = True
            self.fields["mes"].disabled = True

    def clean(self):
        cleaned = super().clean()
        anio = cleaned.get("anio")
        mes = cleaned.get("mes")
        if anio and mes:
            qs = PeriodoRemuneracion.objects.filter(anio=anio, mes=mes)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    "Ya existe un período para ese mes y año. "
                    "El período no depende de las hojas del Excel: "
                    "se crea solo cuando se va a procesar."
                )
        return cleaned

    def validate_unique(self):
        exclude = set(self._get_validation_exclusions())
        exclude.update({"anio", "mes"})
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as exc:
            self._update_errors(exc)


class ReaperturaPeriodoForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo de la reapertura",
        min_length=5,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 4}
        ),
        help_text="Queda registrado en la auditoría del período.",
    )


class ConceptoRemuneracionForm(forms.ModelForm):
    class Meta:
        model = ConceptoRemuneracion
        fields = [
            "codigo",
            "nombre",
            "tipo",
            "naturaleza_calculo",
            "proporcional_dias",
            "editable",
            "orden",
            "activo",
            "descripcion",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "naturaleza_calculo": forms.Select(attrs={"class": "form-select"}),
            "proporcional_dias": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "editable": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "orden": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "activo": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
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
        qs = ConceptoRemuneracion.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un concepto con este código.")
        return codigo

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise ValidationError("El nombre es obligatorio.")
        return nombre

    def validate_unique(self):
        exclude = set(self._get_validation_exclusions())
        exclude.add("codigo")
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as exc:
            self._update_errors(exc)
