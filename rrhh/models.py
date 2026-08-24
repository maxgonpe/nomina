# Corresponde principalmente a REM001 y REM002.
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse

from core.models import AuditModel
from core.validators import formatear_rut, normalizar_rut, validar_rut


class Trabajador(AuditModel):
    rut = models.CharField(
        max_length=15,
        validators=[validar_rut],
    )

    rut_normalizado = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
    )

    nombre_completo = models.CharField(
        max_length=200,
    )

    activo = models.BooleanField(
        default=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["nombre_completo"]
        verbose_name = "trabajador"
        verbose_name_plural = "trabajadores"
        indexes = [
            models.Index(
                fields=["nombre_completo"],
                name="idx_trabajador_nombre",
            ),
        ]

    def clean(self):
        super().clean()

        validar_rut(self.rut)

        self.rut_normalizado = normalizar_rut(
            self.rut
        )

        self.nombre_completo = (
            self.nombre_completo.strip()
        )

    def save(self, *args, **kwargs):
        self.rut_normalizado = normalizar_rut(
            self.rut
        )

        self.nombre_completo = (
            self.nombre_completo.strip()
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_completo} ({self.rut})"

    def get_absolute_url(self):
        return reverse("rrhh:trabajador_detalle", args=[self.pk])

    @property
    def rut_formateado(self):
        return formatear_rut(self.rut_normalizado)


class Cargo(AuditModel):
    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=120,
    )

    descripcion = models.TextField(
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class Contrato(AuditModel):

    class TipoContrato(models.TextChoices):
        INDEFINIDO = "INDEFINIDO", "Indefinido"
        PLAZO_FIJO = "PLAZO_FIJO", "Plazo fijo"
        OBRA_FAENA = "OBRA_FAENA", "Obra o faena"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        TERMINADO = "TERMINADO", "Terminado"

    trabajador = models.ForeignKey(
        Trabajador,
        on_delete=models.PROTECT,
        related_name="contratos",
    )

    cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        related_name="contratos",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contratos",
    )

    tipo_contrato = models.CharField(
        max_length=20,
        choices=TipoContrato.choices,
        default=TipoContrato.INDEFINIDO,
    )

    fecha_inicio = models.DateField()

    fecha_termino = models.DateField(
        null=True,
        blank=True,
    )

    sueldo_base_inicial = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.VIGENTE,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "trabajador__nombre_completo",
            "-fecha_inicio",
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(
                    sueldo_base_inicial__gte=0
                ),
                name="ck_contrato_sueldo_no_negativo",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.fecha_termino
            and self.fecha_termino < self.fecha_inicio
        ):
            raise ValidationError(
                "La fecha de término no puede ser "
                "anterior a la fecha de inicio."
            )

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.fecha_inicio}"
        )


class AnexoContrato(AuditModel):

    class Tipo(models.TextChoices):
        CAMBIO_SUELDO = (
            "CAMBIO_SUELDO",
            "Cambio de sueldo",
        )
        CAMBIO_CARGO = (
            "CAMBIO_CARGO",
            "Cambio de cargo",
        )
        CAMBIO_CENTRO_COSTO = (
            "CAMBIO_CENTRO_COSTO",
            "Cambio de centro de costo",
        )
        OTRO = "OTRO", "Otro"

    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name="anexos",
    )

    fecha_documento = models.DateField()

    fecha_vigencia = models.DateField()

    tipo = models.CharField(
        max_length=30,
        choices=Tipo.choices,
    )

    nuevo_sueldo_base = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )

    nuevo_cargo = models.ForeignKey(
        Cargo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="anexos_nuevo_cargo",
    )

    nuevo_centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="anexos_nuevo_centro",
    )

    descripcion = models.TextField(
        blank=True,
    )

    archivo = models.FileField(
        upload_to="rrhh/anexos/%Y/%m/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "contrato",
            "fecha_vigencia",
        ]

    def clean(self):
        super().clean()

        if (
            self.contrato_id
            and self.fecha_vigencia
            and self.fecha_vigencia
            < self.contrato.fecha_inicio
        ):
            raise ValidationError(
                "La vigencia del anexo no puede "
                "ser anterior al inicio del contrato."
            )

    def __str__(self):
        return (
            f"{self.contrato.trabajador} - "
            f"{self.tipo} - "
            f"{self.fecha_vigencia}"
        )