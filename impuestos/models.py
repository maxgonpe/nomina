# Aquí convertimos Cal. Impuestos en un proceso real.
#Así la hoja de impuestos deja de escribir manualmente:IVA VENTAS
#IVA COMPRAS PPM

import calendar
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum

from core.models import AuditModel


class PeriodoImpuesto(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CALCULADO = "CALCULADO", "Calculado"
        VALIDADO = "VALIDADO", "Validado"
        DECLARADO = "DECLARADO", "Declarado"
        PAGADO = "PAGADO", "Pagado"
        CERRADO = "CERRADO", "Cerrado"

    anio = models.PositiveSmallIntegerField()

    mes = models.PositiveSmallIntegerField()

    fecha_inicio = models.DateField(
        editable=False,
    )

    fecha_fin = models.DateField(
        editable=False,
    )

    iva_ventas = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    iva_compras = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    subtotal_iva = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    neto_ventas = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    tasa_ppm_snapshot = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=0,
    )

    total_ppm = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    monto_a_pagar = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )

    calculado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    cerrado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="periodos_impuestos_cerrados",
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-anio", "-mes"]

        constraints = [
            models.UniqueConstraint(
                fields=["anio", "mes"],
                name="uq_periodo_impuesto",
            ),
            models.CheckConstraint(
                condition=Q(
                    mes__gte=1,
                    mes__lte=12,
                ),
                name="ck_periodo_impuesto_mes",
            ),
        ]

    def save(self, *args, **kwargs):
        ultimo_dia = calendar.monthrange(
            self.anio,
            self.mes,
        )[1]

        self.fecha_inicio = date(
            self.anio,
            self.mes,
            1,
        )

        self.fecha_fin = date(
            self.anio,
            self.mes,
            ultimo_dia,
        )

        super().save(*args, **kwargs)

    @property
    def total_pagado(self):
        total = self.pagos.filter(anulado=False).aggregate(
            total=Sum("monto")
        )["total"]

        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return (
            self.monto_a_pagar
            - self.total_pagado
        )

    def __str__(self):
        return f"{self.mes:02d}-{self.anio}"


class DetalleImpuesto(AuditModel):

    class Tipo(models.TextChoices):
        IVA_VENTA = "IVA_VENTA", "IVA venta"
        IVA_COMPRA = "IVA_COMPRA", "IVA compra"

    periodo = models.ForeignKey(
        PeriodoImpuesto,
        on_delete=models.CASCADE,
        related_name="detalles",
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
    )

    documento_venta = models.ForeignKey(
        "facturacion.DocumentoTributario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="detalles_impuesto",
    )

    documento_compra = models.ForeignKey(
        "facturacion.DocumentoCompra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="detalles_impuesto",
    )

    neto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    iva = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "periodo",
                    "documento_venta",
                ],
                name="uq_imp_periodo_doc_venta",
            ),
            models.UniqueConstraint(
                fields=[
                    "periodo",
                    "documento_compra",
                ],
                name="uq_imp_periodo_doc_compra",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.tipo == self.Tipo.IVA_VENTA
            and not self.documento_venta_id
        ):
            raise ValidationError(
                "Un IVA de venta requiere "
                "un documento de venta."
            )

        if (
            self.tipo == self.Tipo.IVA_COMPRA
            and not self.documento_compra_id
        ):
            raise ValidationError(
                "Un IVA de compra requiere "
                "un documento de compra."
            )

        if (
            self.documento_venta_id
            and self.documento_compra_id
        ):
            raise ValidationError(
                "El detalle no puede representar "
                "simultáneamente compra y venta."
            )

    def __str__(self):
        return (
            f"{self.periodo} - "
            f"{self.tipo}"
        )


class PagoImpuesto(AuditModel):
    periodo = models.ForeignKey(
        PeriodoImpuesto,
        on_delete=models.PROTECT,
        related_name="pagos",
    )

    fecha = models.DateField()

    medio_pago = models.CharField(max_length=50, blank=True)

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    referencia = models.CharField(
        max_length=150,
        blank=True,
    )

    comprobante = models.FileField(
        upload_to="impuestos/pagos/%Y/%m/",
        null=True,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    anulado = models.BooleanField(default=False)
    anulado_en = models.DateTimeField(null=True, blank=True)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="pagos_impuestos_anulados")
    motivo_anulacion = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha"]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_pago_impuesto_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.periodo} - "
            f"{self.monto}"
        )
