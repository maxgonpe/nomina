from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from remuneraciones.models import (
    NOMBRE_MES,
    ConceptoRemuneracion,
    Finiquito,
    HoraExtra,
    LiquidacionMensual,
    MovimientoRemuneracion,
    PagoRemuneracion,
    PeriodoRemuneracion,
)
from remuneraciones.services.finiquitos import registrar as registrar_finiquito
from remuneraciones.services.movimientos import (
    conceptos_carga_manual,
    registrar_movimiento,
)
from rrhh.models import Contrato, Trabajador

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


class MovimientoForm(forms.ModelForm):
    trabajador = forms.ModelChoiceField(
        queryset=Trabajador.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )
    periodo = forms.ModelChoiceField(
        queryset=PeriodoRemuneracion.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True,
    )

    class Meta:
        model = MovimientoRemuneracion
        fields = [
            "concepto",
            "cantidad",
            "valor_unitario",
            "monto",
            "descripcion",
        ]
        widgets = {
            "concepto": forms.Select(attrs={"class": "form-select"}),
            "cantidad": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.0001",
                }
            ),
            "valor_unitario": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.0001",
                }
            ),
            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, periodo=None, trabajador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._periodo_fijo = periodo
        self._trabajador_fijo = trabajador
        if "cantidad" in self.fields:
            self.fields["cantidad"].required = False
        if "valor_unitario" in self.fields:
            self.fields["valor_unitario"].required = False
        if "descripcion" in self.fields:
            self.fields["descripcion"].required = False
        if "monto" in self.fields:
            self.fields["monto"].help_text = (
                "Valor absoluto. Haber o descuento lo define el concepto, "
                "no un signo en este campo."
            )

        trabajadores = Trabajador.objects.filter(activo=True)
        if self.instance.pk:
            actual = self.instance.liquidacion.trabajador_id
            trabajadores = Trabajador.objects.filter(
                Q(pk=actual) | Q(activo=True)
            )
            self.fields["trabajador"].initial = actual
            self.fields["periodo"].initial = self.instance.liquidacion.periodo_id
        self.fields["trabajador"].queryset = trabajadores.order_by(
            "nombre_completo"
        )

        periodos = PeriodoRemuneracion.objects.exclude(
            estado=PeriodoRemuneracion.Estado.CERRADO
        )
        if self.instance.pk:
            periodos = PeriodoRemuneracion.objects.filter(
                Q(pk=self.instance.liquidacion.periodo_id)
                | ~Q(estado=PeriodoRemuneracion.Estado.CERRADO)
            )
        self.fields["periodo"].queryset = periodos.order_by("-anio", "-mes")

        conceptos = conceptos_carga_manual()
        if self.instance.pk and self.instance.concepto_id:
            conceptos = ConceptoRemuneracion.objects.filter(
                Q(pk__in=conceptos.values("pk"))
                | Q(pk=self.instance.concepto_id)
            ).order_by("orden", "nombre")
        self.fields["concepto"].queryset = conceptos

        if periodo is not None and "periodo" in self.fields:
            del self.fields["periodo"]
        if trabajador is not None and "trabajador" in self.fields:
            del self.fields["trabajador"]

    def clean(self):
        cleaned = super().clean()
        trabajador = cleaned.get("trabajador") or self._trabajador_fijo
        periodo = cleaned.get("periodo") or self._periodo_fijo
        if self.instance.pk:
            trabajador = trabajador or self.instance.liquidacion.trabajador
            periodo = periodo or self.instance.liquidacion.periodo
        if periodo and periodo.esta_cerrado:
            raise ValidationError(
                "El período está cerrado. No se pueden modificar movimientos."
            )
        if self.instance.pk and self.instance.bloqueado:
            raise ValidationError(
                "Este movimiento está bloqueado y no se puede editar."
            )
        if self.instance.pk and self.instance.origen == MovimientoRemuneracion.Origen.CALCULADO:
            raise ValidationError("Los movimientos calculados no se pueden editar manualmente.")
        cleaned["trabajador"] = trabajador
        cleaned["periodo"] = periodo
        return cleaned

    def save(self, commit=True):
        usuario = self.instance.actualizado_por or self.instance.creado_por
        return registrar_movimiento(
            trabajador=self.cleaned_data["trabajador"],
            periodo=self.cleaned_data["periodo"],
            concepto=self.cleaned_data["concepto"],
            monto=self.cleaned_data.get("monto"),
            cantidad=self.cleaned_data.get("cantidad"),
            valor_unitario=self.cleaned_data.get("valor_unitario"),
            descripcion=self.cleaned_data.get("descripcion") or "",
            origen=MovimientoRemuneracion.Origen.MANUAL,
            usuario=usuario,
            instance=self.instance if self.instance.pk else None,
        )


class MovimientoCargaForm(MovimientoForm):
    class Meta(MovimientoForm.Meta):
        fields = ["concepto", "monto", "descripcion"]
        widgets = {
            "concepto": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "descripcion": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
        }


MovimientoCargaRapidaFormSet = forms.modelformset_factory(
    MovimientoRemuneracion,
    form=MovimientoCargaForm,
    extra=3,
    can_delete=False,
)


class FiniquitoForm(forms.ModelForm):
    class Meta:
        model = Finiquito
        fields = [
            "trabajador",
            "contrato",
            "periodo",
            "fecha",
            "motivo",
            "monto",
            "observaciones",
            "archivo",
        ]
        widgets = {
            "trabajador": forms.Select(attrs={"class": "form-select"}),
            "contrato": forms.Select(attrs={"class": "form-select"}),
            "periodo": forms.Select(attrs={"class": "form-select"}),
            "fecha": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "motivo": forms.Select(attrs={"class": "form-select"}),
            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, periodo=None, trabajador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._periodo_fijo = periodo
        self._trabajador_fijo = trabajador
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        self.fields["observaciones"].required = False
        self.fields["archivo"].required = False
        self.fields["motivo"].required = False
        self.fields["monto"].help_text = (
            "Monto a liquidar por el finiquito. Alimenta el concepto "
            "FINIQUITO al validar, no una columna de la liquidación."
        )

        trabajadores = Trabajador.objects.filter(activo=True)
        if self.instance.pk and self.instance.trabajador_id:
            trabajadores = Trabajador.objects.filter(
                Q(pk=self.instance.trabajador_id) | Q(activo=True)
            )
        self.fields["trabajador"].queryset = trabajadores.order_by(
            "nombre_completo"
        )

        periodos = PeriodoRemuneracion.objects.exclude(
            estado=PeriodoRemuneracion.Estado.CERRADO
        )
        if self.instance.pk and self.instance.periodo_id:
            periodos = PeriodoRemuneracion.objects.filter(
                Q(pk=self.instance.periodo_id)
                | ~Q(estado=PeriodoRemuneracion.Estado.CERRADO)
            )
        self.fields["periodo"].queryset = periodos.order_by("-anio", "-mes")

        contratos = Contrato.objects.select_related("trabajador", "cargo")
        trabajador_ref = trabajador or (
            self.instance.trabajador if self.instance.pk else None
        )
        if trabajador_ref is not None:
            contratos = contratos.filter(trabajador=trabajador_ref)
        self.fields["contrato"].queryset = contratos.order_by(
            "-fecha_inicio"
        )

        if periodo is not None and "periodo" in self.fields:
            del self.fields["periodo"]
            fecha_widget = self.fields["fecha"].widget
            fecha_widget.attrs["min"] = periodo.fecha_inicio.isoformat()
            fecha_widget.attrs["max"] = periodo.fecha_fin.isoformat()
        if trabajador is not None and "trabajador" in self.fields:
            del self.fields["trabajador"]

    def clean(self):
        cleaned = super().clean()
        trabajador = cleaned.get("trabajador") or self._trabajador_fijo
        periodo = cleaned.get("periodo") or self._periodo_fijo
        if self.instance.pk:
            trabajador = trabajador or self.instance.trabajador
            periodo = periodo or self.instance.periodo
        if periodo and periodo.esta_cerrado:
            raise ValidationError(
                "El período está cerrado. No se pueden modificar finiquitos."
            )
        cleaned["trabajador"] = trabajador
        cleaned["periodo"] = periodo
        return cleaned

    def save(self, commit=True):
        usuario = self.instance.actualizado_por or self.instance.creado_por
        return registrar_finiquito(
            trabajador=self.cleaned_data["trabajador"],
            contrato=self.cleaned_data["contrato"],
            periodo=self.cleaned_data["periodo"],
            fecha=self.cleaned_data["fecha"],
            monto=self.cleaned_data["monto"],
            motivo=self.cleaned_data.get("motivo") or "",
            observaciones=self.cleaned_data.get("observaciones") or "",
            archivo=self.cleaned_data.get("archivo"),
            usuario=usuario,
            instance=self.instance if self.instance.pk else None,
        )


class FiniquitoDocumentoForm(forms.ModelForm):
    class Meta:
        model = Finiquito
        fields = ["observaciones", "archivo"]
        widgets = {
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class DiasFalladosForm(forms.Form):
    dias_fallados = forms.DecimalField(
        min_value=0,
        max_value=30,
        decimal_places=2,
        label="Días fallados",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "max": "30",
                "step": "0.5",
            }
        ),
    )


class PagoRemuneracionForm(forms.ModelForm):
    class Meta:
        model = PagoRemuneracion
        fields = ["fecha", "monto", "medio_pago", "referencia", "observaciones"]
        widgets = {
            "fecha": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "medio_pago": forms.Select(attrs={"class": "form-select"}),
            "referencia": forms.TextInput(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, liquidacion=None, **kwargs):
        self.liquidacion = liquidacion
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        self.fields["referencia"].required = False
        self.fields["observaciones"].required = False
        if not self.instance.pk:
            self.fields["fecha"].initial = timezone.localdate()

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is None or self.liquidacion is None:
            return monto
        if monto <= 0:
            raise ValidationError("El monto del pago debe ser mayor que 0.")
        saldo = self.liquidacion.saldo_pendiente
        if monto > saldo:
            exceso = monto - saldo
            raise ValidationError(
                f"El monto excede el saldo pendiente en ${exceso:,.2f}."
            )
        return monto


class PagoRemuneracionAnularForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo de anulación",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def clean_motivo(self):
        motivo = (self.cleaned_data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError("Debe indicar el motivo de anulación.")
        return motivo
