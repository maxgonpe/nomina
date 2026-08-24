from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from remuneraciones.models import (
    NOMBRE_MES,
    ConceptoRemuneracion,
    HoraExtra,
    PeriodoRemuneracion,
)
from rrhh.models import Trabajador

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


class HoraExtraForm(forms.ModelForm):
    class Meta:
        model = HoraExtra
        fields = [
            "trabajador",
            "periodo",
            "fecha",
            "horas",
            "actividad",
            "observaciones",
        ]
        widgets = {
            "trabajador": forms.Select(attrs={"class": "form-select"}),
            "periodo": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "horas": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "actividad": forms.TextInput(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, periodo=None, trabajador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._periodo_fijo = periodo
        self._trabajador_fijo = trabajador
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        self.fields["actividad"].required = False
        if "observaciones" in self.fields:
            self.fields["observaciones"].required = False

        if "trabajador" in self.fields:
            trabajadores = Trabajador.objects.filter(activo=True)
            if self.instance.pk and self.instance.trabajador_id:
                trabajadores = Trabajador.objects.filter(
                    Q(pk=self.instance.trabajador_id) | Q(activo=True)
                )
            self.fields["trabajador"].queryset = trabajadores.order_by(
                "nombre_completo"
            )

        if "periodo" in self.fields:
            periodos = PeriodoRemuneracion.objects.exclude(
                estado=PeriodoRemuneracion.Estado.CERRADO
            )
            if self.instance.pk and self.instance.periodo_id:
                periodos = PeriodoRemuneracion.objects.filter(
                    Q(pk=self.instance.periodo_id)
                    | ~Q(estado=PeriodoRemuneracion.Estado.CERRADO)
                )
            self.fields["periodo"].queryset = periodos.order_by("-anio", "-mes")

        if periodo is not None and "periodo" in self.fields:
            del self.fields["periodo"]
            fecha_widget = self.fields["fecha"].widget
            fecha_widget.attrs["min"] = periodo.fecha_inicio.isoformat()
            fecha_widget.attrs["max"] = periodo.fecha_fin.isoformat()
        if trabajador is not None and "trabajador" in self.fields:
            del self.fields["trabajador"]

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self._periodo_fijo is not None:
            obj.periodo = self._periodo_fijo
        if self._trabajador_fijo is not None:
            obj.trabajador = self._trabajador_fijo
        if commit:
            obj.save()
        return obj


class HoraExtraCargaForm(HoraExtraForm):
    class Meta(HoraExtraForm.Meta):
        fields = ["trabajador", "fecha", "horas", "actividad"]
        widgets = {
            "trabajador": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "fecha": forms.DateInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "horas": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "actividad": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
        }


HoraExtraCargaRapidaFormSet = forms.modelformset_factory(
    HoraExtra,
    form=HoraExtraCargaForm,
    extra=3,
    can_delete=False,
)
