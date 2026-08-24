from django import forms
from django.core.exceptions import ValidationError

from core.models import CentroCosto
from core.validators import normalizar_rut, validar_rut
from rrhh.models import AnexoContrato, Cargo, Contrato, Trabajador


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


class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
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


class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = [
            "trabajador",
            "cargo",
            "centro_costo",
            "tipo_contrato",
            "fecha_inicio",
            "fecha_termino",
            "sueldo_base_inicial",
            "estado",
            "observaciones",
        ]
        widgets = {
            "trabajador": forms.Select(attrs={"class": "form-select"}),
            "cargo": forms.Select(attrs={"class": "form-select"}),
            "centro_costo": forms.Select(attrs={"class": "form-select"}),
            "tipo_contrato": forms.Select(attrs={"class": "form-select"}),
            "fecha_inicio": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "fecha_termino": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "sueldo_base_inicial": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "step": "1"}
            ),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_inicio"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_termino"].input_formats = ["%Y-%m-%d"]
        cargos = Cargo.objects.filter(activo=True)
        centros = CentroCosto.objects.filter(activo=True)
        if self.instance.pk:
            cargos = Cargo.objects.filter(
                Q_activo_o_actual(self.instance.cargo_id)
            )
            centros = CentroCosto.objects.filter(
                Q_activo_o_actual(self.instance.centro_costo_id)
            )
        self.fields["cargo"].queryset = cargos.order_by("nombre")
        self.fields["centro_costo"].queryset = centros.order_by("codigo")
        self.fields["centro_costo"].required = False
        self.fields["trabajador"].queryset = Trabajador.objects.filter(
            activo=True
        ).order_by("nombre_completo")
        if self.instance.pk and self.instance.trabajador_id:
            self.fields["trabajador"].queryset = Trabajador.objects.filter(
                pk=self.instance.trabajador_id
            ) | Trabajador.objects.filter(activo=True)


def Q_activo_o_actual(pk):
    from django.db.models import Q

    q = Q(activo=True)
    if pk:
        q |= Q(pk=pk)
    return q


class AnexoContratoForm(forms.ModelForm):
    class Meta:
        model = AnexoContrato
        fields = [
            "fecha_documento",
            "fecha_vigencia",
            "tipo",
            "nuevo_sueldo_base",
            "nuevo_cargo",
            "nuevo_centro_costo",
            "descripcion",
            "archivo",
        ]
        widgets = {
            "fecha_documento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "fecha_vigencia": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "nuevo_sueldo_base": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "step": "1"}
            ),
            "nuevo_cargo": forms.Select(attrs={"class": "form-select"}),
            "nuevo_centro_costo": forms.Select(attrs={"class": "form-select"}),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fecha_documento"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_vigencia"].input_formats = ["%Y-%m-%d"]
        self.fields["nuevo_cargo"].queryset = Cargo.objects.filter(
            activo=True
        ).order_by("nombre")
        self.fields["nuevo_cargo"].required = False
        self.fields["nuevo_centro_costo"].queryset = CentroCosto.objects.filter(
            activo=True
        ).order_by("codigo")
        self.fields["nuevo_centro_costo"].required = False
        self.fields["nuevo_sueldo_base"].required = False



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
