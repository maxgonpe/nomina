# Esta app recibe información desde prácticamente todos los módulos.
# La relación importante queda así:
# REMUNERACIONES ─┐
# RENDICIONES ────┤
# FACTURACIÓN ────┤
# COMPRAS ────────┼──► MovimientoFinanciero
# IMPUESTOS ──────┘

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum

from core.models import AuditModel


class CategoriaFinanciera(AuditModel):

    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"
        CONTROL = "CONTROL", "Control"
        OTRO = "OTRO", "Otro"

    codigo = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    tipo = models.CharField(
        max_length=15,
        choices=Tipo.choices,
    )

    padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcategorias",
    )

    orden = models.PositiveIntegerField(
        default=0,
    )

    activo = models.BooleanField(
        default=True,
    )

    descripcion = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "orden",
            "codigo",
        ]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class MovimientoFinanciero(AuditModel):

    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"

    class Origen(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        REMUNERACION = (
            "REMUNERACION",
            "Remuneración",
        )
        RENDICION = "RENDICION", "Rendición"
        FACTURACION = (
            "FACTURACION",
            "Facturación",
        )
        COMPRA = "COMPRA", "Compra"
        IMPUESTO = "IMPUESTO", "Impuesto"
        OTRO = "OTRO", "Otro"

    fecha = models.DateField(
        db_index=True,
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
    )

    categoria = models.ForeignKey(
        CategoriaFinanciera,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    descripcion = models.CharField(
        max_length=250,
    )

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    origen = models.CharField(
        max_length=20,
        choices=Origen.choices,
        default=Origen.MANUAL,
    )

    trabajador = models.ForeignKey(
        "rrhh.Trabajador",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    liquidacion = models.ForeignKey(
        "remuneraciones.LiquidacionMensual",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    rendicion = models.ForeignKey(
        "rendiciones.Rendicion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    documento_tributario = models.ForeignKey(
        "facturacion.DocumentoTributario",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    documento_compra = models.ForeignKey(
        "facturacion.DocumentoCompra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    periodo_impuesto = models.ForeignKey(
        "impuestos.PeriodoImpuesto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_financieros",
    )

    referencia = models.CharField(
        max_length=150,
        blank=True,
    )

    archivo_respaldo = models.FileField(
        upload_to="finanzas/movimientos/%Y/%m/",
        null=True,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-fecha"]

        indexes = [
            models.Index(
                fields=["fecha", "tipo"],
                name="idx_mov_fin_fecha_tipo",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_mov_fin_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.fecha} - "
            f"{self.descripcion} - "
            f"{self.monto}"
        )


class CierreFinancieroMensual(AuditModel):

    class Estado(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierto"
        CALCULADO = "CALCULADO", "Calculado"
        CERRADO = "CERRADO", "Cerrado"

    anio = models.PositiveSmallIntegerField()

    mes = models.PositiveSmallIntegerField()

    saldo_inicial = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    ingresos = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    egresos = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    saldo_final = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.ABIERTO,
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
        related_name="cierres_financieros_realizados",
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-anio", "-mes"]

        constraints = [
            models.UniqueConstraint(
                fields=["anio", "mes"],
                name="uq_cierre_financiero",
            ),
            models.CheckConstraint(
                condition=Q(
                    mes__gte=1,
                    mes__lte=12,
                ),
                name="ck_cierre_fin_mes",
            ),
        ]

    def __str__(self):
        return f"{self.mes:02d}-{self.anio}"


class ObligacionFinanciera(AuditModel):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PARCIAL = "PARCIAL", "Pago parcial"
        PAGADA = "PAGADA", "Pagada"
        ANULADA = "ANULADA", "Anulada"

    categoria = models.ForeignKey(
        CategoriaFinanciera,
        on_delete=models.PROTECT,
        related_name="obligaciones",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="obligaciones_financieras",
    )

    descripcion = models.CharField(
        max_length=250,
    )

    fecha_inicio = models.DateField()

    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
    )

    monto_total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    observaciones = models.TextField(
        blank=True,
    )

    @property
    def total_pagado(self):
        total = self.pagos.aggregate(
            total=Sum("monto")
        )["total"]

        return total or Decimal("0.00")

    @property
    def saldo(self):
        return (
            self.monto_total
            - self.total_pagado
        )

    def __str__(self):
        return self.descripcion


class PagoObligacionFinanciera(AuditModel):
    obligacion = models.ForeignKey(
        ObligacionFinanciera,
        on_delete=models.PROTECT,
        related_name="pagos",
    )

    fecha = models.DateField()

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    referencia = models.CharField(
        max_length=150,
        blank=True,
    )

    class Meta:
        ordering = ["-fecha"]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_pago_obligacion_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.obligacion} - "
            f"{self.monto}"
        )