# Corresponde principalmente a REM001 y REM002.
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import get_valid_filename

from core.models import AuditModel
from core.validators import formatear_rut, normalizar_rut, validar_rut


def anexos_upload_to(instance, filename):
    nombre = get_valid_filename(filename)
    anio = timezone.now().year
    if instance.fecha_documento:
        anio = instance.fecha_documento.year
    trabajador_id = "sinterm"
    if instance.contrato_id:
        trabajador_id = instance.contrato.trabajador_id
    return f"rrhh/anexos/{anio}/{trabajador_id}/{nombre}"


def rangos_se_solapan(inicio_a, fin_a, inicio_b, fin_b):
    fin_a = fin_a or date.max
    fin_b = fin_b or date.max
    return inicio_a <= fin_b and inicio_b <= fin_a


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
        verbose_name = "cargo"
        verbose_name_plural = "cargos"

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("rrhh:cargo_editar", args=[self.pk])


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

        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    sueldo_base_inicial__gt=0
                ),
                name="ck_contrato_sueldo_positivo",
            ),
        ]

    def cubre_fecha(self, fecha):
        if fecha < self.fecha_inicio:
            return False
        if self.fecha_termino and fecha > self.fecha_termino:
            return False
        return True

    def clean(self):
        super().clean()

        if (
            self.fecha_termino
            and self.fecha_inicio
            and self.fecha_termino < self.fecha_inicio
        ):
            raise ValidationError(
                {
                    "fecha_termino": (
                        "La fecha de término no puede ser "
                        "anterior a la fecha de inicio."
                    )
                }
            )

        if (
            self.sueldo_base_inicial is not None
            and self.sueldo_base_inicial <= 0
        ):
            raise ValidationError(
                {
                    "sueldo_base_inicial": (
                        "El sueldo base debe ser mayor que cero."
                    )
                }
            )

        if self.trabajador_id and self.fecha_inicio:
            otros = Contrato.objects.filter(
                trabajador_id=self.trabajador_id,
            ).exclude(pk=self.pk)
            for otro in otros:
                if rangos_se_solapan(
                    self.fecha_inicio,
                    self.fecha_termino,
                    otro.fecha_inicio,
                    otro.fecha_termino,
                ):
                    raise ValidationError(
                        {
                            "fecha_inicio": (
                                "El trabajador ya tiene un contrato "
                                "que cubre estas fechas."
                            )
                        }
                    )

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.fecha_inicio}"
        )

    def get_absolute_url(self):
        return reverse("rrhh:contrato_detalle", args=[self.pk])


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
        upload_to=anexos_upload_to,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "contrato",
            "fecha_vigencia",
        ]
        verbose_name = "anexo de contrato"
        verbose_name_plural = "anexos de contrato"

    def clean(self):
        super().clean()
        errores = {}

        if (
            self.contrato_id
            and self.fecha_vigencia
            and self.fecha_vigencia
            < self.contrato.fecha_inicio
        ):
            errores["fecha_vigencia"] = (
                "La vigencia del anexo no puede "
                "ser anterior al inicio del contrato."
            )

        if (
            self.contrato_id
            and self.fecha_vigencia
            and self.contrato.fecha_termino
            and self.fecha_vigencia > self.contrato.fecha_termino
        ):
            errores["fecha_vigencia"] = (
                "La vigencia del anexo no puede "
                "ser posterior al término del contrato."
            )

        if (
            self.nuevo_sueldo_base is not None
            and self.nuevo_sueldo_base <= 0
        ):
            errores["nuevo_sueldo_base"] = (
                "El nuevo sueldo base debe ser mayor que cero."
            )

        if self.tipo == self.Tipo.CAMBIO_SUELDO and self.nuevo_sueldo_base is None:
            errores["nuevo_sueldo_base"] = (
                "Indique el nuevo sueldo base."
            )
        if self.tipo == self.Tipo.CAMBIO_CARGO and not self.nuevo_cargo_id:
            errores["nuevo_cargo"] = "Indique el nuevo cargo."
        if (
            self.tipo == self.Tipo.CAMBIO_CENTRO_COSTO
            and not self.nuevo_centro_costo_id
        ):
            errores["nuevo_centro_costo"] = (
                "Indique el nuevo centro de costo."
            )

        if self.contrato_id and self.fecha_vigencia:
            hermanos = AnexoContrato.objects.filter(
                contrato_id=self.contrato_id,
                fecha_vigencia=self.fecha_vigencia,
            ).exclude(pk=self.pk)
            for otro in hermanos:
                if (
                    self.nuevo_sueldo_base is not None
                    and otro.nuevo_sueldo_base is not None
                ) or (
                    self.nuevo_cargo_id
                    and otro.nuevo_cargo_id
                ) or (
                    self.nuevo_centro_costo_id
                    and otro.nuevo_centro_costo_id
                ):
                    errores["fecha_vigencia"] = (
                        "Ya existe un anexo que modifica el mismo "
                        "dato en esa fecha de vigencia."
                    )
                    break

        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return (
            f"{self.contrato.trabajador} - "
            f"{self.tipo} - "
            f"{self.fecha_vigencia}"
        )

    def get_absolute_url(self):
        return reverse("rrhh:contrato_detalle", args=[self.contrato_id])