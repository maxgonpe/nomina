from django.db import models
from django.conf import settings

from core.models import AuditModel


class LineaBalance(AuditModel):
    class Seccion(models.TextChoices):
        LIQUIDEZ = "LIQUIDEZ", "Liquidez"
        COBRAR = "COBRAR", "Cuentas por cobrar"
        OBLIGACIONES = "OBLIGACIONES", "Obligaciones"
        TRIBUTARIA = "TRIBUTARIA", "Posición tributaria"
        RESULTADO = "RESULTADO", "Resultado de gestión"
        FINANCIAMIENTO = "FINANCIAMIENTO", "Financiamiento / capital"
        EXCEL = "EXCEL", "Equivalencia Excel"

    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    seccion = models.CharField(max_length=20, choices=Seccion.choices)
    orden = models.PositiveIntegerField(default=0)
    tipo = models.CharField(max_length=30)
    fuente = models.CharField(max_length=50)
    codigo_fuente = models.CharField(max_length=50, blank=True)
    activa = models.BooleanField(default=True)
    permite_ajuste = models.BooleanField(default=False)

    class Meta:
        ordering = ["seccion", "orden", "codigo"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CierreBalance(AuditModel):
    fecha_corte = models.DateField(unique=True)
    estado = models.CharField(max_length=12, choices=[("CERRADO", "Cerrado"), ("REABIERTO", "Reabierto")], default="CERRADO")
    caja = models.DecimalField(max_digits=16, decimal_places=2)
    cuentas_por_cobrar = models.DecimalField(max_digits=16, decimal_places=2)
    obligaciones = models.DecimalField(max_digits=16, decimal_places=2)
    resultado = models.DecimalField(max_digits=16, decimal_places=2)
    posicion_disponible = models.DecimalField(max_digits=16, decimal_places=2)
    resumen_fuentes = models.JSONField(default=dict)
    cerrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
