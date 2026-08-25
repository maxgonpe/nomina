from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from core.models import CentroCosto
from rendiciones.models import DocumentoRendicion, Rendicion, RendicionDetalle
from rrhh.models import Trabajador

EXTENSIONES_DOCUMENTO = ("pdf", "jpg", "jpeg", "png")
TAMANO_MAX_DOCUMENTO = 10 * 1024 * 1024  # 10 MB


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


class RendicionDetalleForm(forms.ModelForm):
    class Meta:
        model = RendicionDetalle
        fields = ["centro_costo", "descripcion", "monto"]
        widgets = {
            "centro_costo": forms.Select(
                attrs={"class": "form-select form-select-sm"}
            ),
            "descripcion": forms.TextInput(
                attrs={"class": "form-control form-control-sm"}
            ),
            "monto": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm monto-detalle",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.centro_costo_id:
            qs = CentroCosto.objects.filter(
                Q(activo=True) | Q(pk=self.instance.centro_costo_id)
            )
        else:
            qs = CentroCosto.objects.filter(activo=True)
        self.fields["centro_costo"].queryset = qs.order_by("codigo")
        self.fields["centro_costo"].empty_label = "Centro…"
        self.fields["descripcion"].required = False

    def clean_monto(self):
        monto = self.cleaned_data.get("monto")
        if monto is None:
            raise ValidationError("El monto es obligatorio.")
        if monto <= 0:
            raise ValidationError("El monto debe ser mayor que cero.")
        return monto

    def clean_centro_costo(self):
        centro = self.cleaned_data.get("centro_costo")
        if centro is None:
            raise ValidationError("Debe indicar un centro de costo.")
        if not self.instance.pk and not centro.activo:
            raise ValidationError(
                "Solo se pueden usar centros de costo activos."
            )
        if (
            self.instance.pk
            and centro.pk != self.instance.centro_costo_id
            and not centro.activo
        ):
            raise ValidationError(
                "Solo se puede cambiar a un centro de costo activo."
            )
        return centro


class BaseRendicionDetalleFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        # Varias líneas al mismo CC están permitidas (REN002).


def rendicion_detalle_formset_factory(extra=1):
    return inlineformset_factory(
        Rendicion,
        RendicionDetalle,
        form=RendicionDetalleForm,
        formset=BaseRendicionDetalleFormSet,
        extra=extra,
        can_delete=True,
        min_num=0,
        validate_min=False,
    )


RendicionDetalleFormSet = rendicion_detalle_formset_factory(extra=1)


class DocumentoRendicionForm(forms.ModelForm):
    class Meta:
        model = DocumentoRendicion
        fields = ["tipo", "archivo", "descripcion"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "archivo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png",
                }
            ),
            "descripcion": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["archivo"].validators.append(
            FileExtensionValidator(
                allowed_extensions=list(EXTENSIONES_DOCUMENTO),
                message="Solo se permiten archivos PDF, JPG o PNG.",
            )
        )
        self.fields["descripcion"].required = False

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            raise ValidationError("Debe adjuntar un archivo.")
        if archivo.size > TAMANO_MAX_DOCUMENTO:
            raise ValidationError(
                "El archivo no puede superar los 10 MB."
            )
        return archivo


class RechazarRendicionForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo del rechazo",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        min_length=3,
    )

    def clean_motivo(self):
        motivo = (self.cleaned_data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError("El motivo de rechazo es obligatorio.")
        return motivo


class AnularRendicionForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo de anulación",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        min_length=3,
    )

    def clean_motivo(self):
        motivo = (self.cleaned_data.get("motivo") or "").strip()
        if not motivo:
            raise ValidationError("El motivo de anulación es obligatorio.")
        return motivo
