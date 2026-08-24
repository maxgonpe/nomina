#Aquí se representa la tabla Excel:
#Columna1 | CASA | EGC | CGA | OFI | TOTAL
# BODEGA
#sin tocar models.py.
#Solo creamos:
#CentroCosto(codigo="BODEGA", ...)

from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum

from core.models import AuditModel


class Rendicion(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PRESENTADA = "PRESENTADA", "Presentada"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        PAGADA = "PAGADA", "Pagada"
        ANULADA = "ANULADA", "Anulada"

    trabajador = models.ForeignKey(
        "rrhh.Trabajador",
        on_delete=models.PROTECT,
        related_name="rendiciones",
    )

    fecha = models.DateField(
        db_index=True,
    )

    descripcion = models.CharField(
        max_length=250,
    )

    total_declarado = models.DecimalField(
        max_digits=16,
        decimal_places=2,
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
        ordering = ["-fecha"]

        constraints = [
            models.CheckConstraint(
                condition=Q(total_declarado__gte=0),
                name="ck_rendicion_total",
            ),
        ]

    @property
    def total_distribuido(self):
        total = self.detalles.aggregate(
            total=Sum("monto")
        )["total"]

        return total or Decimal("0.00")

    @property
    def diferencia(self):
        return (
            self.total_declarado
            - self.total_distribuido
        )

    @property
    def cuadra(self):
        return self.diferencia == Decimal("0.00")

    def __str__(self):
        return (
            f"Rendición #{self.pk} - "
            f"{self.trabajador}"
        )


class RendicionDetalle(AuditModel):
    rendicion = models.ForeignKey(
        Rendicion,
        on_delete=models.CASCADE,
        related_name="detalles",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        related_name="detalles_rendicion",
    )

    descripcion = models.CharField(
        max_length=250,
        blank=True,
    )

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    class Meta:
        ordering = [
            "rendicion",
            "centro_costo__codigo",
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_rendicion_detalle_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.rendicion} - "
            f"{self.centro_costo.codigo}: "
            f"{self.monto}"
        )


class DocumentoRendicion(AuditModel):

    class Tipo(models.TextChoices):
        BOLETA = "BOLETA", "Boleta"
        FACTURA = "FACTURA", "Factura"
        COMPROBANTE = "COMPROBANTE", "Comprobante"
        OTRO = "OTRO", "Otro"

    rendicion = models.ForeignKey(
        Rendicion,
        on_delete=models.CASCADE,
        related_name="documentos",
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.OTRO,
    )

    archivo = models.FileField(
        upload_to="rendiciones/%Y/%m/",
    )

    descripcion = models.CharField(
        max_length=250,
        blank=True,
    )

    def __str__(self):
        return (
            f"{self.rendicion} - "
            f"{self.tipo}"
        )
