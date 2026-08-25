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
from django.utils import timezone
from django.utils.text import get_valid_filename

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
        total = self.pagos.filter(anulado=False).aggregate(
            total=Sum("monto")
        )["total"]

        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return (
            self.total_a_pagar
            - self.total_pagado
        )

    @property
    def estado_pago(self):
        pagado = self.total_pagado
        if pagado <= 0:
            return "SIN PAGO"
        if pagado >= self.total_a_pagar:
            return "PAGADA"
        return "PAGO PARCIAL"

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.periodo}"
        )

    def get_absolute_url(self):
        return reverse("remuneraciones:liquidacion_detalle", args=[self.pk])

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

    anulado = models.BooleanField(
        default=False,
    )

    anulado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_remuneracion_anulados",
    )

    motivo_anulacion = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-fecha", "-pk"]

        constraints = [
            models.CheckConstraint(
                condition=Q(monto__gt=0),
                name="ck_pago_remuneracion_monto",
            ),
        ]

        permissions = [
            (
                "anular_pagoremuneracion",
                "Puede anular pagos de remuneración",
            ),
        ]

    @property
    def esta_vigente(self):
        return not self.anulado

    @property
    def estado_display(self):
        return "ANULADO" if self.anulado else "VIGENTE"

    def __str__(self):
        return (
            f"{self.liquidacion} - "
            f"{self.monto}"
        )

    def clean(self):
        super().clean()
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)
        if self.monto is not None and self.monto <= 0:
            raise ValidationError(
                {"monto": "El monto del pago debe ser mayor que 0."}
            )

    def save(self, *args, **kwargs):
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)
        super().save(*args, **kwargs)


def finiquito_upload_to(instance, filename):
    nombre = get_valid_filename(filename)
    anio = timezone.now().year
    if instance.fecha:
        anio = instance.fecha.year
    trabajador_id = instance.trabajador_id or "sinterm"
    return f"remuneraciones/finiquitos/{anio}/{trabajador_id}/{nombre}"


class Finiquito(AuditModel):

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        VALIDADO = "VALIDADO", "Validado"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

    class Motivo(models.TextChoices):
        MUTUO_ACUERDO = "MUTUO_ACUERDO", "Mutuo acuerdo"
        RENUNCIA = "RENUNCIA", "Renuncia"
        DESAHUCIO = "DESAHUCIO", "Desahucio"
        NECESIDADES_EMPRESA = (
            "NECESIDADES_EMPRESA",
            "Necesidades de la empresa",
        )
        TERMINO_PLAZO = "TERMINO_PLAZO", "Término de plazo"
        TERMINO_OBRA = "TERMINO_OBRA", "Término de obra o faena"
        OTRO = "OTRO", "Otro"

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
        max_length=30,
        choices=Motivo.choices,
        default=Motivo.OTRO,
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
        upload_to=finiquito_upload_to,
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

    @property
    def esta_anulado(self):
        return self.estado == self.Estado.ANULADO

    @property
    def alimenta_liquidacion(self):
        return self.estado in (
            self.Estado.VALIDADO,
            self.Estado.PAGADO,
        )

    def __str__(self):
        return (
            f"{self.trabajador} - "
            f"{self.fecha}"
        )

    def get_absolute_url(self):
        return reverse("remuneraciones:finiquito_detalle", args=[self.pk])

    def clean(self):
        super().clean()
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        if self.monto is not None and self.monto <= 0:
            raise ValidationError(
                {"monto": "El monto del finiquito debe ser mayor que 0."}
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
                {
                    "fecha": (
                        "La fecha del finiquito no pertenece "
                        "al período seleccionado."
                    )
                }
            )
        if (
            self.trabajador_id
            and self.contrato_id
            and self.contrato.trabajador_id != self.trabajador_id
        ):
            raise ValidationError(
                {"contrato": "El contrato no corresponde a este trabajador."}
            )
        if self.contrato_id and self.fecha:
            if self.fecha < self.contrato.fecha_inicio:
                raise ValidationError(
                    {
                        "fecha": (
                            "La fecha del finiquito no puede ser anterior "
                            "al inicio del contrato."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.periodo_id:
            bloquear_si_periodo_cerrado(self.periodo)
        if self.estado != self.Estado.BORRADOR:
            raise ValidationError(
                "Solo se puede borrar un finiquito en borrador. "
                "Los validados se anulan para conservar la trazabilidad."
            )
        super().delete(*args, **kwargs)


class ConceptoCostoTrabajador(AuditModel):
    codigo = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    codigo_origen = models.CharField(
        max_length=50,
        blank=True,
        help_text=(
            "Código de ConceptoRemuneracion del cual se toma el monto. "
            "Vacío para totales de referencia (p. ej. TOTAL_LIQUIDADO)."
        ),
    )

    incluye_en_total = models.BooleanField(
        default=True,
        help_text=(
            "Si es falso, el monto es informativo y no suma al costo "
            "(p. ej. TOTAL_LIQUIDADO)."
        ),
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
        self.codigo_origen = (self.codigo_origen or "").strip().upper()
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

    def get_absolute_url(self):
        return reverse("remuneraciones:costo_detalle", args=[self.pk])

    def clean(self):
        super().clean()
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)

    def save(self, *args, **kwargs):
        if self.liquidacion_id:
            bloquear_si_periodo_cerrado(self.liquidacion.periodo)
        super().save(*args, **kwargs)


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
            models.UniqueConstraint(
                fields=["costo_trabajador", "concepto"],
                name="uq_costo_detalle_concepto",
            ),
        ]

    def __str__(self):
        return (
            f"{self.costo_trabajador} - "
            f"{self.concepto}: {self.monto}"
        )

    def clean(self):
        super().clean()
        if self.costo_trabajador_id:
            bloquear_si_periodo_cerrado(
                self.costo_trabajador.liquidacion.periodo
            )

    def save(self, *args, **kwargs):
        if self.costo_trabajador_id:
            bloquear_si_periodo_cerrado(
                self.costo_trabajador.liquidacion.periodo
            )
        super().save(*args, **kwargs)