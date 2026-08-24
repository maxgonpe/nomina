#Observa que no existe un modelo Balance.Eso es intencional.
# El balance será:
# El BALANCE de Excel será un reporte calculado a partir de estos modelos.
#CuentaContable
#       │
#       ▼
#DetalleAsiento
#       │
#       ▼
#SUM(DEBE)
#SUM(HABER)
#       │
#       ├── Saldo deudor
#       ├── Saldo acreedor
#       ├── Activo
#       ├── Pasivo
#       ├── Pérdida
#       └── Ganancia

from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum

from core.models import AuditModel


class CuentaContable(AuditModel):

    class Tipo(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        PASIVO = "PASIVO", "Pasivo"
        PATRIMONIO = "PATRIMONIO", "Patrimonio"
        INGRESO = "INGRESO", "Ingreso"
        GASTO = "GASTO", "Gasto"
        ORDEN = "ORDEN", "Orden"

    class Naturaleza(models.TextChoices):
        DEUDORA = "DEUDORA", "Deudora"
        ACREEDORA = "ACREEDORA", "Acreedora"

    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    tipo = models.CharField(
        max_length=15,
        choices=Tipo.choices,
    )

    naturaleza = models.CharField(
        max_length=15,
        choices=Naturaleza.choices,
    )

    padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcuentas",
    )

    permite_movimientos = models.BooleanField(
        default=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    descripcion = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["codigo"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class AsientoContable(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONTABILIZADO = (
            "CONTABILIZADO",
            "Contabilizado",
        )
        ANULADO = "ANULADO", "Anulado"

    numero = models.PositiveBigIntegerField(
        unique=True,
        null=True,
        blank=True,
    )

    fecha = models.DateField(
        db_index=True,
    )

    glosa = models.CharField(
        max_length=250,
    )

    referencia = models.CharField(
        max_length=150,
        blank=True,
    )

    movimiento_financiero = models.ForeignKey(
        "finanzas.MovimientoFinanciero",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asientos_contables",
    )

    origen_tipo = models.CharField(
        max_length=50,
        blank=True,
    )

    origen_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-fecha",
            "-numero",
        ]

    @property
    def total_debe(self):
        total = self.detalles.aggregate(
            total=Sum("debe")
        )["total"]

        return total or Decimal("0.00")

    @property
    def total_haber(self):
        total = self.detalles.aggregate(
            total=Sum("haber")
        )["total"]

        return total or Decimal("0.00")

    @property
    def cuadrado(self):
        return self.total_debe == self.total_haber

    def __str__(self):
        return (
            f"Asiento {self.numero or 'BORRADOR'} "
            f"- {self.fecha}"
        )


class DetalleAsiento(AuditModel):
    asiento = models.ForeignKey(
        AsientoContable,
        on_delete=models.CASCADE,
        related_name="detalles",
    )

    cuenta = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="detalles_contables",
    )

    descripcion = models.CharField(
        max_length=250,
        blank=True,
    )

    debe = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    haber = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = [
            "asiento",
            "id",
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        debe__gt=0,
                        haber=0,
                    )
                    |
                    Q(
                        haber__gt=0,
                        debe=0,
                    )
                ),
                name="ck_detalle_asiento_debe_haber",
            ),
        ]

    def __str__(self):
        return (
            f"{self.asiento} - "
            f"{self.cuenta.codigo}"
        )