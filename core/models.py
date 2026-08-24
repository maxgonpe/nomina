#Aquí dejamos infraestructura compartida por todo el proyecto:
#auditoría; centros de costo; aliases; parámetros de negocio con vigencia.
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse


class AuditModel(models.Model):
    creado_en = models.DateTimeField(
        auto_now_add=True,
        editable=False,
    )
    actualizado_en = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        abstract = True


class CentroCosto(AuditModel):

    class Tipo(models.TextChoices):
        GENERAL = "GENERAL", "General"
        ADMINISTRATIVO = "ADMINISTRATIVO", "Administrativo"
        OBRA = "OBRA", "Obra"
        PERSONAL = "PERSONAL", "Personal"
        OTRO = "OTRO", "Otro"

    codigo = models.CharField(
        max_length=30,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        default=Tipo.GENERAL,
    )

    padre = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcentros",
    )

    descripcion = models.TextField(
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["codigo"]
        verbose_name = "centro de costo"
        verbose_name_plural = "centros de costo"

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class AliasCentroCosto(AuditModel):
    centro_costo = models.ForeignKey(
        CentroCosto,
        on_delete=models.CASCADE,
        related_name="aliases",
    )

    alias = models.CharField(
        max_length=100,
        unique=True,
    )

    class Meta:
        ordering = ["alias"]
        verbose_name = "alias de centro de costo"
        verbose_name_plural = "aliases de centros de costo"

    def save(self, *args, **kwargs):
        self.alias = self.alias.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.alias} → {self.centro_costo.codigo}"


class ParametroNegocio(AuditModel):
    codigo = models.CharField(
        max_length=60,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    descripcion = models.TextField(
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["codigo"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def get_absolute_url(self):
        return reverse("core:parametro_detalle", args=[self.pk])


class ParametroValor(AuditModel):
    parametro = models.ForeignKey(
        ParametroNegocio,
        on_delete=models.PROTECT,
        related_name="valores",
    )

    valor = models.DecimalField(
        max_digits=20,
        decimal_places=8,
    )

    vigencia_desde = models.DateField()

    vigencia_hasta = models.DateField(
        null=True,
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "parametro__codigo",
            "-vigencia_desde",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["parametro", "vigencia_desde"],
                name="uq_parametro_vigencia_desde",
            ),
            models.CheckConstraint(
                condition=(
                    Q(vigencia_hasta__isnull=True)
                    | Q(vigencia_hasta__gte=models.F("vigencia_desde"))
                ),
                name="ck_parametro_vigencia_fechas",
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.vigencia_hasta
            and self.vigencia_hasta < self.vigencia_desde
        ):
            raise ValidationError(
                "La fecha de término no puede ser anterior "
                "a la fecha de inicio."
            )

        if not self.parametro_id or not self.vigencia_desde:
            return

        qs = ParametroValor.objects.filter(
            parametro_id=self.parametro_id
        ).exclude(
            pk=self.pk
        )

        qs = qs.filter(
            Q(vigencia_hasta__isnull=True)
            | Q(vigencia_hasta__gte=self.vigencia_desde)
        )

        if self.vigencia_hasta:
            qs = qs.filter(
                vigencia_desde__lte=self.vigencia_hasta
            )

        if qs.exists():
            raise ValidationError(
                "Existe otra vigencia del parámetro "
                "que se superpone con este período."
            )

    def __str__(self):
        hasta = self.vigencia_hasta or "sin término"

        return (
            f"{self.parametro.codigo}: "
            f"{self.valor} "
            f"({self.vigencia_desde} / {hasta})"
        )