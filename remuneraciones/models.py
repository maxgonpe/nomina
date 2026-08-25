# Este es el corazón del proyecto.Aquí quedan REM003 a REM010.
import calendar
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse

from core.models import AuditModel


NOMBRE_MES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

HOJA_EXCEL_MES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


def bloquear_si_periodo_cerrado(periodo):
    if periodo is not None:
        periodo.assert_editable()


class PeriodoRemuneracion(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ABIERTO = "ABIERTO", "Abierto"
        CALCULADO = "CALCULADO", "Calculado"
        VALIDADO = "VALIDADO", "Validado"
        CERRADO = "CERRADO", "Cerrado"

    anio = models.PositiveSmallIntegerField()

    mes = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(12),
        ],
    )

    fecha_inicio = models.DateField(
        editable=False,
    )

    fecha_fin = models.DateField(
        editable=False,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
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
        related_name="periodos_remuneracion_cerrados",
    )

    motivo_reapertura = models.TextField(
        blank=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-anio",
            "-mes",
        ]
        verbose_name = "período de remuneración"
        verbose_name_plural = "períodos de remuneración"

        constraints = [
            models.UniqueConstraint(
                fields=["anio", "mes"],
                name="uq_periodo_remuneracion",
            ),
            models.CheckConstraint(
                condition=Q(
                    mes__gte=1,
                    mes__lte=12,
                ),
                name="ck_periodo_remuneracion_mes",
            ),
        ]

    @property
    def nombre(self):
        mes = NOMBRE_MES.get(self.mes, str(self.mes))
        return f"{mes} {self.anio}"

    @property
    def nombre_hoja_excel(self):
        return HOJA_EXCEL_MES.get(self.mes, "")

    @property
    def esta_cerrado(self):
        return self.estado == self.Estado.CERRADO

    def assert_editable(self):
        if self.esta_cerrado:
            raise ValidationError(
                "El período está cerrado. No se pueden modificar horas extra, "
                "movimientos, liquidaciones ni finiquitos, salvo reapertura "
                "autorizada."
            )

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

    def __str__(self):
        return f"{self.mes:02d}-{self.anio}"

    def get_absolute_url(self):
        return reverse("remuneraciones:periodo_detalle", args=[self.pk])


class ConceptoRemuneracion(AuditModel):

    class Tipo(models.TextChoices):
        HABER = "HABER", "Haber"
        DESCUENTO = "DESCUENTO", "Descuento"
        INFORMATIVO = "INFORMATIVO", "Informativo"

    class NaturalezaCalculo(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATICO = "AUTOMATICO", "Automático"
        MIXTO = "MIXTO", "Mixto"

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

    naturaleza_calculo = models.CharField(
        max_length=15,
        choices=NaturalezaCalculo.choices,
        default=NaturalezaCalculo.MANUAL,
    )

    proporcional_dias = models.BooleanField(
        default=False,
    )

    editable = models.BooleanField(
        default=True,
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
            "nombre",
        ]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def get_absolute_url(self):
        return reverse("remuneraciones:concepto_editar", args=[self.pk])


class LiquidacionMensual(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CALCULADA = "CALCULADA", "Calculada"
        VALIDADA = "VALIDADA", "Validada"
        PAGADA = "PAGADA", "Pagada"
        CERRADA = "CERRADA", "Cerrada"
        ANULADA = "ANULADA", "Anulada"

    periodo = models.ForeignKey(
        PeriodoRemuneracion,
        on_delete=models.PROTECT,
        related_name="liquidaciones",
    )

    trabajador = models.ForeignKey(
        "rrhh.Trabajador",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
    )

    contrato = models.ForeignKey(
        "rrhh.Contrato",
        on_delete=models.PROTECT,
        related_name="liquidaciones",
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )

    sueldo_base_snapshot = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    cargo_codigo_snapshot = models.CharField(
        max_length=30,
        blank=True,
    )

    cargo_nombre_snapshot = models.CharField(
        max_length=120,
        blank=True,
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="liquidaciones",
    )

    centro_costo_codigo_snapshot = models.CharField(
        max_length=30,
        blank=True,
    )

    centro_costo_nombre_snapshot = models.CharField(
        max_length=150,
        blank=True,
    )

    dias_fallados = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    dias_trabajados = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30,
    )

    valor_dia = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=0,
    )

    horas_extra_total = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    valor_hora_extra = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=0,
    )

    monto_horas_extra = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total_haberes = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total_descuentos = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total_liquidado = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    total_a_pagar = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    version_calculo = models.CharField(
        max_length=30,
        default="1.0",
    )

    calculado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    requiere_recalculo = models.BooleanField(
        default=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-periodo__anio",
            "-periodo__mes",
            "trabajador__nombre_completo",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "periodo",
                    "trabajador",
                ],
                name="uq_liquidacion_periodo_trabajador",
            ),
            models.CheckConstraint(
                condition=Q(
                    dias_fallados__gte=0
                ),
                name="ck_liquidacion_dias_fallados",
            ),
            models.CheckConstraint(
                condition=Q(
                    dias_trabajados__gte=0
                ),
                name="ck_liquidacion_dias_trabajados",
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
        return (
            self.total_a_pagar
            - self.total_pagado
        )

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.periodo}"
        )

    def clean(self):
        super().clean()
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)

    def save(self, *args, **kwargs):
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        super().save(*args, **kwargs)


def marcar_liquidacion_pendiente_recalculo(trabajador_id, periodo_id):
    if not trabajador_id or not periodo_id:
        return
    LiquidacionMensual.objects.filter(
        trabajador_id=trabajador_id,
        periodo_id=periodo_id,
    ).exclude(
        estado=LiquidacionMensual.Estado.ANULADA
    ).update(requiere_recalculo=True)


class MovimientoRemuneracion(AuditModel):

    class Origen(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        CALCULADO = "CALCULADO", "Calculado"
        IMPORTADO_EXCEL = (
            "IMPORTADO_EXCEL",
            "Importado desde Excel",
        )

    liquidacion = models.ForeignKey(
        LiquidacionMensual,
        on_delete=models.CASCADE,
        related_name="movimientos",
    )

    concepto = models.ForeignKey(
        ConceptoRemuneracion,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )

    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
    )

    valor_unitario = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        null=True,
        blank=True,
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

    descripcion = models.TextField(
        blank=True,
    )

    generado_automaticamente = models.BooleanField(
        default=False,
    )

    bloqueado = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = [
            "liquidacion",
            "concepto__orden",
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gte=0),
                name="ck_movimiento_rem_monto",
            ),
        ]

    @property
    def es_descuento(self):
        return self.concepto.tipo == ConceptoRemuneracion.Tipo.DESCUENTO

    @property
    def monto_con_signo(self):
        """El signo lo determina concepto.tipo, no el texto ni el monto."""
        if self.es_descuento:
            return -self.monto
        return self.monto

    def __str__(self):
        return (
            f"{self.liquidacion} - "
            f"{self.concepto.codigo}: "
            f"{self.monto}"
        )

    def get_absolute_url(self):
        return reverse("remuneraciones:movimiento_editar", args=[self.pk])

    def clean(self):
        super().clean()
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)
        if self.monto is not None and self.monto < 0:
            raise ValidationError(
                {
                    "monto": (
                        "El monto se informa en valor absoluto. "
                        "El signo lo define el tipo del concepto "
                        "(haber o descuento)."
                    )
                }
            )
        if self.bloqueado and self.pk:
            original = (
                MovimientoRemuneracion.objects.filter(pk=self.pk)
                .values("bloqueado")
                .first()
            )
            if original and original["bloqueado"]:
                raise ValidationError(
                    "Este movimiento está bloqueado y no se puede modificar."
                )

    def save(self, *args, **kwargs):
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)
        super().save(*args, **kwargs)
        marcar_liquidacion_pendiente_recalculo(
            self.liquidacion.trabajador_id,
            self.liquidacion.periodo_id,
        )

    def delete(self, *args, **kwargs):
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)
        if self.bloqueado:
            raise ValidationError(
                "Este movimiento está bloqueado y no se puede borrar."
            )
        trabajador_id = self.liquidacion.trabajador_id
        periodo_id = self.liquidacion.periodo_id
        super().delete(*args, **kwargs)
        marcar_liquidacion_pendiente_recalculo(
            trabajador_id,
            periodo_id,
        )


class HoraExtra(AuditModel):

    class Origen(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        IMPORTADO_EXCEL = (
            "IMPORTADO_EXCEL",
            "Importado desde Excel",
        )

    trabajador = models.ForeignKey(
        "rrhh.Trabajador",
        on_delete=models.PROTECT,
        related_name="horas_extra",
    )

    periodo = models.ForeignKey(
        PeriodoRemuneracion,
        on_delete=models.PROTECT,
        related_name="horas_extra",
    )

    fecha = models.DateField(
        db_index=True,
    )

    horas = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    actividad = models.TextField(
        blank=True,
    )

    origen = models.CharField(
        max_length=20,
        choices=Origen.choices,
        default=Origen.MANUAL,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "-fecha",
            "trabajador__nombre_completo",
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(horas__gt=0),
                name="ck_hora_extra_horas_positivas",
            ),
        ]

    def clean(self):
        super().clean()
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)

        if self.horas is not None and self.horas <= 0:
            raise ValidationError(
                {"horas": "Las horas extra deben ser mayores que 0."}
            )

        if (
            self.periodo_id
            and self.fecha
            and not (
                self.periodo.fecha_inicio
                <= self.fecha
                <= self.periodo.fecha_fin
            )
        ):
            raise ValidationError(
                "La fecha de la hora extra no pertenece "
                "al período seleccionado."
            )

    def save(self, *args, **kwargs):
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        super().save(*args, **kwargs)
        marcar_liquidacion_pendiente_recalculo(
            self.trabajador_id,
            self.periodo_id,
        )

    def delete(self, *args, **kwargs):
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        trabajador_id = self.trabajador_id
        periodo_id = self.periodo_id
        super().delete(*args, **kwargs)
        marcar_liquidacion_pendiente_recalculo(
            trabajador_id,
            periodo_id,
        )

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.fecha} - "
            f"{self.horas} hrs"
        )

    def get_absolute_url(self):
        return reverse("remuneraciones:hora_extra_editar", args=[self.pk])


class PagoRemuneracion(AuditModel):

    class MedioPago(models.TextChoices):
        TRANSFERENCIA = (
            "TRANSFERENCIA",
            "Transferencia",
        )
        EFECTIVO = "EFECTIVO", "Efectivo"
        CHEQUE = "CHEQUE", "Cheque"
        OTRO = "OTRO", "Otro"

    liquidacion = models.ForeignKey(
        LiquidacionMensual,
        on_delete=models.PROTECT,
        related_name="pagos",
    )

    fecha = models.DateField()

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    medio_pago = models.CharField(
        max_length=20,
        choices=MedioPago.choices,
        default=MedioPago.TRANSFERENCIA,
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
                name="ck_pago_remuneracion_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.liquidacion} - "
            f"{self.monto}"
        )


class Finiquito(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        VALIDADO = "VALIDADO", "Validado"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

    trabajador = models.ForeignKey(
        "rrhh.Trabajador",
        on_delete=models.PROTECT,
        related_name="finiquitos",
    )

    contrato = models.ForeignKey(
        "rrhh.Contrato",
        on_delete=models.PROTECT,
        related_name="finiquitos",
    )

    periodo = models.ForeignKey(
        PeriodoRemuneracion,
        on_delete=models.PROTECT,
        related_name="finiquitos",
    )

    liquidacion = models.ForeignKey(
        LiquidacionMensual,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finiquitos",
    )

    fecha = models.DateField()

    motivo = models.CharField(
        max_length=200,
        blank=True,
    )

    monto = models.DecimalField(
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

    archivo = models.FileField(
        upload_to="remuneraciones/finiquitos/%Y/%m/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-fecha"]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gte=0),
                name="ck_finiquito_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.fecha}"
        )

    def clean(self):
        super().clean()
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)

    def save(self, *args, **kwargs):
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        super().save(*args, **kwargs)


class ConceptoCostoTrabajador(AuditModel):
    codigo = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    activo = models.BooleanField(
        default=True,
    )

    orden = models.PositiveIntegerField(
        default=0,
    )

    descripcion = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["orden", "nombre"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class CostoTrabajadorPeriodo(AuditModel):
    liquidacion = models.OneToOneField(
        LiquidacionMensual,
        on_delete=models.CASCADE,
        related_name="costo_trabajador",
    )

    centro_costo = models.ForeignKey(
        "core.CentroCosto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="costos_trabajadores",
    )

    centro_costo_codigo_snapshot = models.CharField(
        max_length=30,
        blank=True,
    )

    centro_costo_nombre_snapshot = models.CharField(
        max_length=150,
        blank=True,
    )

    dias_trabajados = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    total = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default=0,
    )

    calculado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["liquidacion"]

    def __str__(self):
        return f"Costo {self.liquidacion}"


class CostoTrabajadorDetalle(AuditModel):
    costo_trabajador = models.ForeignKey(
        CostoTrabajadorPeriodo,
        on_delete=models.CASCADE,
        related_name="detalles",
    )

    concepto = models.ForeignKey(
        ConceptoCostoTrabajador,
        on_delete=models.PROTECT,
        related_name="detalles",
    )

    monto = models.DecimalField(
        max_digits=16,
        decimal_places=2,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "costo_trabajador",
            "concepto__orden",
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gte=0),
                name="ck_costo_trab_det_monto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.costo_trabajador} - "
            f"{self.concepto}: {self.monto}"
        )