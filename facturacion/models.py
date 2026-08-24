# Aquí coloco también proveedores y documentos de compra
# porque todavía no tenemos una app independiente compras.

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

from core.models import AuditModel
from core.validators import normalizar_rut, validar_rut


class Cliente(AuditModel):
    rut = models.CharField(
        max_length=15,
        validators=[validar_rut],
    )

    rut_normalizado = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
    )

    razon_social = models.CharField(
        max_length=200,
    )

    activo = models.BooleanField(
        default=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["razon_social"]

    def clean(self):
        super().clean()
        validar_rut(self.rut)
        self.rut_normalizado = normalizar_rut(
            self.rut
        )

    def save(self, *args, **kwargs):
        self.rut_normalizado = normalizar_rut(
            self.rut
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.razon_social


class Obra(AuditModel):

    class Estado(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        ACTIVA = "ACTIVA", "Activa"
        TERMINADA = "TERMINADA", "Terminada"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"

    codigo = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=200,
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="obras",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="obras",
    )

    fecha_inicio = models.DateField(
        null=True,
        blank=True,
    )

    fecha_termino = models.DateField(
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PLANIFICADA,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["codigo"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class DocumentoTributario(AuditModel):

    class Tipo(models.TextChoices):
        FACTURA = "FACTURA", "Factura"
        FACTURA_EXENTA = (
            "FACTURA_EXENTA",
            "Factura exenta",
        )
        NOTA_CREDITO = (
            "NOTA_CREDITO",
            "Nota de crédito",
        )
        NOTA_DEBITO = (
            "NOTA_DEBITO",
            "Nota de débito",
        )
        BOLETA = "BOLETA", "Boleta"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        EMITIDA = "EMITIDA", "Emitida"
        PARCIAL = "PARCIAL", "Pago parcial"
        PAGADA = "PAGADA", "Pagada"
        ANULADA = "ANULADA", "Anulada"

    fecha_emision = models.DateField(
        db_index=True,
    )

    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="documentos",
    )

    obra = models.ForeignKey(
        Obra,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documentos",
    )

    tipo_documento = models.CharField(
        max_length=20,
        choices=Tipo.choices,
    )

    numero = models.CharField(
        max_length=50,
    )

    neto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    tasa_iva_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=Decimal("0.190000"),
    )

    iva = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.EMITIDA,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-fecha_emision"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tipo_documento",
                    "numero",
                ],
                name="uq_documento_venta_tipo_numero",
            ),
            models.CheckConstraint(
                condition=Q(neto__gte=0),
                name="ck_documento_venta_neto",
            ),
            models.CheckConstraint(
                condition=Q(iva__gte=0),
                name="ck_documento_venta_iva",
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="ck_documento_venta_total",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.obra_id
            and self.cliente_id
            and self.obra.cliente_id
            != self.cliente_id
        ):
            raise ValidationError(
                "La obra seleccionada no pertenece "
                "al cliente seleccionado."
            )

    @property
    def total_cobrado(self):
        total = self.cobros.aggregate(
            total=Sum("monto")
        )["total"]

        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return self.total - self.total_cobrado

    def __str__(self):
        return (
            f"{self.tipo_documento} "
            f"{self.numero} - "
            f"{self.cliente}"
        )


class CobroDocumentoTributario(AuditModel):
    documento = models.ForeignKey(
        DocumentoTributario,
        on_delete=models.PROTECT,
        related_name="cobros",
    )

    fecha = models.DateField()

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    medio_pago = models.CharField(
        max_length=50,
        blank=True,
    )

    referencia = models.CharField(
        max_length=150,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-fecha"]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_cobro_documento_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.documento} - "
            f"{self.monto}"
        )


class Proveedor(AuditModel):
    rut = models.CharField(
        max_length=15,
        validators=[validar_rut],
    )

    rut_normalizado = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
    )

    razon_social = models.CharField(
        max_length=200,
    )

    activo = models.BooleanField(
        default=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["razon_social"]

    def clean(self):
        super().clean()
        validar_rut(self.rut)
        self.rut_normalizado = normalizar_rut(
            self.rut
        )

    def save(self, *args, **kwargs):
        self.rut_normalizado = normalizar_rut(
            self.rut
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.razon_social


class DocumentoCompra(AuditModel):

    class Estado(models.TextChoices):
        REGISTRADO = "REGISTRADO", "Registrado"
        PARCIAL = "PARCIAL", "Pago parcial"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

    fecha_documento = models.DateField(
        db_index=True,
    )

    fecha_recepcion = models.DateField(
        null=True,
        blank=True,
    )

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="documentos_compra",
    )

    tipo_documento = models.CharField(
        max_length=30,
        default="FACTURA",
    )

    numero = models.CharField(
        max_length=50,
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documentos_compra",
    )

    neto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    tasa_iva_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=Decimal("0.190000"),
    )

    iva = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.REGISTRADO,
    )

    archivo = models.FileField(
        upload_to="facturacion/compras/%Y/%m/",
        null=True,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-fecha_documento"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "proveedor",
                    "tipo_documento",
                    "numero",
                ],
                name="uq_documento_compra",
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="ck_documento_compra_total",
            ),
        ]

    @property
    def total_pagado(self):
        total = self.pagos.aggregate(
            total=Sum("monto")
        )["total"]

        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return self.total - self.total_pagado

    def __str__(self):
        return (
            f"{self.proveedor} - "
            f"{self.tipo_documento} "
            f"{self.numero}"
        )


class PagoDocumentoCompra(AuditModel):
    documento = models.ForeignKey(
        DocumentoCompra,
        on_delete=models.PROTECT,
        related_name="pagos",
    )

    fecha = models.DateField()

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    medio_pago = models.CharField(
        max_length=50,
        blank=True,
    )

    referencia = models.CharField(
        max_length=150,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-fecha"]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_pago_compra_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.documento} - "
            f"{self.monto}"
        )