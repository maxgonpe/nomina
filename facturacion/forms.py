from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from core.validators import normalizar_rut, validar_rut
from core.models import CentroCosto
from facturacion.models import Cliente, CobroDocumentoTributario, DocumentoCompra, DocumentoTributario, Obra, Proveedor
from facturacion.services.documentos import calcular_documento


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["rut", "razon_social", "activo", "observaciones"]
        widgets = {
            "rut": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "76.123.456-7",
                "autocomplete": "off",
            }),
            "razon_social": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_rut(self):
        rut = self.cleaned_data["rut"]
        validar_rut(rut)
        normalizado = normalizar_rut(rut)
        clientes = Cliente.objects.filter(rut_normalizado=normalizado)
        if self.instance.pk:
            clientes = clientes.exclude(pk=self.instance.pk)
        if clientes.exists():
            raise ValidationError("Ya existe un cliente con este RUT.")
        return rut.strip()

    def clean_razon_social(self):
        razon_social = " ".join((self.cleaned_data.get("razon_social") or "").split())
        if not razon_social:
            raise ValidationError("La razón social es obligatoria.")
        return razon_social

    def clean_activo(self):
        activo = self.cleaned_data.get("activo")
        if not self.instance.pk and "activo" not in self.data:
            return True
        return activo


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["rut", "razon_social", "activo", "observaciones"]
        widgets = {
            "rut": forms.TextInput(attrs={"class": "form-control", "placeholder": "76.123.456-7", "autocomplete": "off"}),
            "razon_social": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_rut(self):
        rut = self.cleaned_data["rut"]
        validar_rut(rut)
        qs = Proveedor.objects.filter(rut_normalizado=normalizar_rut(rut))
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un proveedor con este RUT.")
        return rut.strip()

    def clean_razon_social(self):
        razon = " ".join((self.cleaned_data.get("razon_social") or "").split())
        if not razon:
            raise ValidationError("La razón social es obligatoria.")
        return razon

    def clean_activo(self):
        if not self.instance.pk and "activo" not in self.data:
            return True
        return self.cleaned_data.get("activo")


class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = ["codigo", "nombre", "cliente", "centro_costo", "fecha_inicio", "fecha_termino", "estado", "observaciones"]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "centro_costo": forms.Select(attrs={"class": "form-select"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "fecha_termino": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        cliente = kwargs.pop("cliente", None)
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(activo=True).order_by("razon_social")
        if self.instance.pk and not self.instance.cliente.activo:
            self.fields["cliente"].queryset = Cliente.objects.filter(pk=self.instance.cliente_id) | self.fields["cliente"].queryset
        self.fields["centro_costo"].queryset = CentroCosto.objects.filter(activo=True).order_by("codigo")
        self.fields["centro_costo"].required = False
        self.fields["fecha_inicio"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_termino"].input_formats = ["%Y-%m-%d"]
        if cliente:
            self.initial["cliente"] = cliente.pk

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not codigo:
            raise ValidationError("El código es obligatorio.")
        obras = Obra.objects.filter(codigo=codigo)
        if self.instance.pk:
            obras = obras.exclude(pk=self.instance.pk)
        if obras.exists():
            raise ValidationError("Ya existe una obra con este código.")
        return codigo

    def clean_nombre(self):
        nombre = " ".join((self.cleaned_data.get("nombre") or "").split())
        if not nombre:
            raise ValidationError("El nombre es obligatorio.")
        return nombre

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("fecha_inicio")
        termino = cleaned.get("fecha_termino")
        if inicio and termino and termino < inicio:
            self.add_error("fecha_termino", "La fecha de término no puede ser anterior a la fecha de inicio.")
        return cleaned


class DocumentoTributarioForm(forms.ModelForm):
    class Meta:
        model = DocumentoTributario
        fields = ["fecha_emision", "fecha_vencimiento", "cliente", "obra", "tipo_documento", "numero", "neto", "observaciones"]
        widgets = {
            "fecha_emision": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "fecha_vencimiento": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "cliente": forms.Select(attrs={"class": "form-select"}),
            "obra": forms.Select(attrs={"class": "form-select"}),
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "neto": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        cliente = kwargs.pop("cliente", None)
        super().__init__(*args, **kwargs)
        self.fields["fecha_emision"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_vencimiento"].input_formats = ["%Y-%m-%d"]
        self.fields["cliente"].queryset = Cliente.objects.filter(activo=True).order_by("razon_social")
        self.fields["obra"].queryset = Obra.objects.select_related("cliente").order_by("codigo")
        self.fields["obra"].required = False
        if cliente:
            self.initial["cliente"] = cliente.pk

    def clean_numero(self):
        numero = (self.cleaned_data.get("numero") or "").strip()
        if not numero:
            raise ValidationError("El número es obligatorio.")
        qs = DocumentoTributario.objects.filter(tipo_documento=self.cleaned_data.get("tipo_documento"), numero=numero)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un documento con este tipo y número.")
        return numero

    def clean(self):
        cleaned = super().clean()
        cliente = cleaned.get("cliente")
        obra = cleaned.get("obra")
        if obra and cliente and obra.cliente_id != cliente.pk:
            self.add_error("obra", "La obra seleccionada no pertenece al cliente.")
        fecha = cleaned.get("fecha_emision")
        vencimiento = cleaned.get("fecha_vencimiento")
        if fecha and vencimiento and vencimiento < fecha:
            self.add_error("fecha_vencimiento", "El vencimiento no puede ser anterior a la emisión.")
        if fecha and cleaned.get("neto") is not None:
            tipo = cleaned.get("tipo_documento")
            if tipo == DocumentoTributario.Tipo.FACTURA_EXENTA:
                tasa = 0
                iva = 0
            else:
                importes = calcular_documento(fecha, tipo, cleaned["neto"])
                tasa = importes["tasa_iva_snapshot"]
                iva = importes["iva"]
            self.instance.tasa_iva_snapshot = tasa
            self.instance.iva = iva
            self.instance.total = cleaned["neto"] + iva
        return cleaned


class AnularDocumentoTributarioForm(forms.Form):
    confirmacion = forms.BooleanField(label="Confirmo la anulación", required=True)


class CobroDocumentoForm(forms.ModelForm):
    class Meta:
        model = CobroDocumentoTributario
        fields = ["fecha", "monto", "medio_pago", "referencia", "observaciones"]
        widgets = {"fecha": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"), "monto": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}), "medio_pago": forms.TextInput(attrs={"class": "form-control"}), "referencia": forms.TextInput(attrs={"class": "form-control"}), "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3})}

    def __init__(self, *args, documento=None, **kwargs):
        self.documento = documento or kwargs.get("instance").documento
        super().__init__(*args, **kwargs)
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto <= 0:
            raise ValidationError("El monto debe ser mayor que cero.")
        cobrado = self.documento.total_cobrado
        if self.instance.pk:
            cobrado -= self.instance.monto
        if cobrado + monto > self.documento.total:
            raise ValidationError("El cobro excede el saldo pendiente del documento.")
        return monto

    def clean(self):
        cleaned = super().clean()
        if self.documento.estado == DocumentoTributario.Estado.ANULADA:
            raise ValidationError("No se pueden registrar cobros para un documento anulado.")
        return cleaned


class FiltroFacturacionForm(forms.Form):
    anio = forms.IntegerField(required=False, min_value=2000, max_value=2100)
    mes = forms.IntegerField(required=False, min_value=1, max_value=12)
    desde = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    hasta = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.filter(activo=True), required=False)
    obra = forms.ModelChoiceField(queryset=Obra.objects.all(), required=False)
    tipo = forms.ChoiceField(choices=[("", "Todos")]+list(DocumentoTributario.Tipo.choices), required=False)
    estado = forms.ChoiceField(choices=[("", "Todos")]+list(DocumentoTributario.Estado.choices), required=False)
    centro_costo = forms.ModelChoiceField(queryset=CentroCosto.objects.filter(activo=True), required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("desde") and cleaned.get("hasta") and cleaned["hasta"] < cleaned["desde"]:
            raise ValidationError("La fecha hasta no puede ser anterior a la fecha desde.")
        if cleaned.get("mes") and not cleaned.get("anio"):
            raise ValidationError("El mes requiere indicar el año.")
        return cleaned


class DocumentoCompraForm(forms.ModelForm):
    class Meta:
        model = DocumentoCompra
        fields = ["fecha_documento", "fecha_recepcion", "proveedor", "tipo_documento", "numero", "centro_costo", "neto", "archivo", "observaciones"]
        widgets = {"fecha_documento": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"), "fecha_recepcion": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"), "proveedor": forms.Select(attrs={"class": "form-select"}), "tipo_documento": forms.TextInput(attrs={"class": "form-control"}), "numero": forms.TextInput(attrs={"class": "form-control"}), "centro_costo": forms.Select(attrs={"class": "form-select"}), "neto": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}), "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}), "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3})}

    def __init__(self, *args, proveedor=None, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("fecha_documento", "fecha_recepcion"):
            self.fields[campo].input_formats = ["%Y-%m-%d"]
        self.fields["proveedor"].queryset = Proveedor.objects.filter(activo=True).order_by("razon_social")
        self.fields["centro_costo"].queryset = CentroCosto.objects.filter(activo=True).order_by("codigo")
        self.fields["centro_costo"].required = False
        if proveedor:
            self.initial["proveedor"] = proveedor.pk

    def clean_numero(self):
        numero = (self.cleaned_data.get("numero") or "").strip()
        if not numero:
            raise ValidationError("El número es obligatorio.")
        qs = DocumentoCompra.objects.filter(proveedor=self.cleaned_data.get("proveedor"), tipo_documento=self.cleaned_data.get("tipo_documento"), numero=numero)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un documento con este proveedor, tipo y número.")
        return numero

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if archivo:
            if archivo.size > 10 * 1024 * 1024:
                raise ValidationError("El archivo no puede superar 10 MB.")
            if archivo.name.lower().rsplit(".", 1)[-1] not in {"pdf", "jpg", "jpeg", "png"}:
                raise ValidationError("El archivo debe ser PDF, JPG, JPEG o PNG.")
        return archivo

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fecha_documento") and cleaned.get("fecha_recepcion") and cleaned["fecha_recepcion"] < cleaned["fecha_documento"]:
            self.add_error("fecha_recepcion", "La recepción no puede ser anterior al documento.")
        if cleaned.get("neto") is not None:
            from facturacion.services.documentos_compra import calcular_documento_compra
            importes = calcular_documento_compra(cleaned.get("fecha_documento"), cleaned.get("tipo_documento"), cleaned["neto"])
            self.instance.tasa_iva_snapshot = importes["tasa_iva_snapshot"]
            self.instance.iva = importes["iva"]
            self.instance.total = importes["total"]
        return cleaned
