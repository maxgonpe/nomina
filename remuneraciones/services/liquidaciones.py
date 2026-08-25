from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from core.services.parametros import valor_hora_extra, valor_opcional
from remuneraciones.models import (
    Finiquito,
    HoraExtra,
    LiquidacionMensual,
    MovimientoRemuneracion,
    PagoRemuneracion,
    PeriodoRemuneracion,
)
from remuneraciones.services.finiquitos import (
    sincronizar_movimiento_finiquito,
    suma_finiquitos,
)
from remuneraciones.services.horas_extra import suma_horas_extra
from remuneraciones.services.movimientos import (
    dinero,
    obtener_o_crear_liquidacion_borrador,
    upsert_movimiento_sistema,
)
from rrhh.models import Contrato, Trabajador
from rrhh.services.contratos import condicion_vigente

VERSION_CALCULO = "1.0"
DIAS_MES = Decimal("30")
CUATRO = Decimal("0.0001")

CONCEPTOS_PROPORCIONALES = (
    ("COLACION", "VALOR_COLACION_MENSUAL"),
    ("MOVILIZACION", "VALOR_MOVILIZACION_MENSUAL"),
    ("DESGASTE_HERRAMIENTAS", "VALOR_DESGASTE_HERRAMIENTAS"),
)


def tasa(valor):
    return Decimal(str(valor)).quantize(CUATRO, rounding=ROUND_HALF_UP)


def calcular(trabajador, periodo, *, usuario=None, dias_fallados=None):
    """
    Motor oficial de REM005. Snapshots a la fecha del período; totales desde
    movimientos (manuales + automáticos). No agrega columnas por concepto.
    """
    periodo.assert_editable()
    if dias_fallados is not None and Decimal(str(dias_fallados)) < 0:
        raise ValidationError(
            {"dias_fallados": "Los días fallados no pueden ser negativos."}
        )
    if dias_fallados is not None and Decimal(str(dias_fallados)) > DIAS_MES:
        raise ValidationError(
            {"dias_fallados": "Los días fallados no pueden superar 30."}
        )

    with transaction.atomic():
        liquidacion = obtener_o_crear_liquidacion_borrador(
            trabajador, periodo, usuario=usuario
        )
        if liquidacion.estado in (
            LiquidacionMensual.Estado.PAGADA,
            LiquidacionMensual.Estado.CERRADA,
            LiquidacionMensual.Estado.ANULADA,
        ):
            raise ValidationError(
                "No se puede recalcular una liquidación "
                f"{liquidacion.get_estado_display().lower()}."
            )

        fecha = periodo.fecha_fin
        condicion = (
            condicion_vigente(trabajador, fecha)
            or condicion_vigente(trabajador, periodo.fecha_inicio)
        )
        if condicion is None:
            raise ValidationError(
                "El trabajador no tiene contrato vigente en este período."
            )

        fallados = (
            Decimal(str(dias_fallados))
            if dias_fallados is not None
            else liquidacion.dias_fallados
        )
        dias_trabajados = DIAS_MES - fallados
        sueldo = dinero(condicion.sueldo_base)
        valor_dia = tasa(sueldo / DIAS_MES)
        horas = suma_horas_extra(trabajador, periodo)
        valor_he = tasa(valor_hora_extra(sueldo, fecha))
        monto_he = dinero(horas * valor_he)

        cargo = condicion.cargo
        centro = condicion.centro_costo
        liquidacion.contrato = condicion.contrato
        liquidacion.sueldo_base_snapshot = sueldo
        liquidacion.cargo_codigo_snapshot = getattr(cargo, "codigo", "") or ""
        liquidacion.cargo_nombre_snapshot = getattr(cargo, "nombre", "") or ""
        liquidacion.centro_costo = centro
        liquidacion.centro_costo_codigo_snapshot = (
            getattr(centro, "codigo", "") or ""
        )
        liquidacion.centro_costo_nombre_snapshot = (
            getattr(centro, "nombre", "") or ""
        )
        liquidacion.dias_fallados = fallados
        liquidacion.dias_trabajados = dias_trabajados
        liquidacion.valor_dia = valor_dia
        liquidacion.horas_extra_total = horas
        liquidacion.valor_hora_extra = valor_he
        liquidacion.monto_horas_extra = monto_he
        liquidacion.save()

        upsert_movimiento_sistema(
            liquidacion=liquidacion,
            codigo="SUELDO_BASE",
            monto=sueldo,
            descripcion="Sueldo pactado (snapshot)",
            usuario=usuario,
        )
        upsert_movimiento_sistema(
            liquidacion=liquidacion,
            codigo="HORAS_EXTRA",
            monto=monto_he,
            descripcion=f"{horas} h × {valor_he}",
            usuario=usuario,
        )
        upsert_movimiento_sistema(
            liquidacion=liquidacion,
            codigo="INASISTENCIA",
            monto=dinero(valor_dia * fallados),
            descripcion=f"{fallados} días × valor día",
            usuario=usuario,
        )
        for codigo_concepto, codigo_parametro in CONCEPTOS_PROPORCIONALES:
            mensual = valor_opcional(codigo_parametro, fecha)
            if mensual is None:
                upsert_movimiento_sistema(
                    liquidacion=liquidacion,
                    codigo=codigo_concepto,
                    monto=0,
                    usuario=usuario,
                )
                continue
            upsert_movimiento_sistema(
                liquidacion=liquidacion,
                codigo=codigo_concepto,
                monto=dinero(dias_trabajados * (mensual / DIAS_MES)),
                descripcion=(
                    f"{dias_trabajados} días × ({mensual} / 30)"
                ),
                usuario=usuario,
            )

        for finiquito in Finiquito.objects.filter(
            trabajador=trabajador,
            periodo=periodo,
            estado__in=[
                Finiquito.Estado.VALIDADO,
                Finiquito.Estado.PAGADO,
            ],
        ):
            sincronizar_movimiento_finiquito(finiquito, usuario=usuario)

        haberes = _suma_tipo(liquidacion, "HABER")
        descuentos = _suma_tipo(liquidacion, "DESCUENTO")
        liquidado = dinero(haberes - descuentos)
        liquidacion.total_haberes = haberes
        liquidacion.total_descuentos = descuentos
        liquidacion.total_liquidado = liquidado
        liquidacion.total_a_pagar = liquidado
        liquidacion.estado = LiquidacionMensual.Estado.CALCULADA
        liquidacion.version_calculo = VERSION_CALCULO
        liquidacion.calculado_en = timezone.now()
        liquidacion.requiere_recalculo = False
        if usuario is not None:
            liquidacion.actualizado_por = usuario
        liquidacion.save()

        from remuneraciones.services.costos import generar_desde_liquidacion

        generar_desde_liquidacion(liquidacion, usuario=usuario)
    liquidacion.refresh_from_db()
    return liquidacion


def _suma_tipo(liquidacion, tipo):
    total = liquidacion.movimientos.filter(
        concepto__tipo=tipo,
    ).aggregate(total=Sum("monto"))["total"]
    return dinero(total or 0)


def trabajadores_a_liquidar(periodo):
    ids = set()
    contratos = Contrato.objects.filter(
        fecha_inicio__lte=periodo.fecha_fin,
    ).filter(
        Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=periodo.fecha_inicio)
    )
    ids.update(contratos.values_list("trabajador_id", flat=True))
    ids.update(
        HoraExtra.objects.filter(periodo=periodo).values_list(
            "trabajador_id", flat=True
        )
    )
    ids.update(
        LiquidacionMensual.objects.filter(periodo=periodo)
        .exclude(estado=LiquidacionMensual.Estado.ANULADA)
        .values_list("trabajador_id", flat=True)
    )
    ids.update(
        Finiquito.objects.filter(periodo=periodo).values_list(
            "trabajador_id", flat=True
        )
    )
    return Trabajador.objects.filter(pk__in=ids).order_by("nombre_completo")


def calcular_periodo(periodo, usuario=None):
    """Calcula todas las liquidaciones del período. No cambia el estado del período."""
    periodo.assert_editable()
    ok = []
    errores = []
    terminales = {
        LiquidacionMensual.Estado.PAGADA,
        LiquidacionMensual.Estado.CERRADA,
        LiquidacionMensual.Estado.ANULADA,
    }
    for trabajador in trabajadores_a_liquidar(periodo):
        existente = LiquidacionMensual.objects.filter(
            trabajador=trabajador,
            periodo=periodo,
        ).first()
        if existente is not None and existente.estado in terminales:
            continue
        try:
            ok.append(
                calcular(trabajador, periodo, usuario=usuario)
            )
        except ValidationError as exc:
            if hasattr(exc, "messages"):
                detalle = " ".join(str(m) for m in exc.messages)
            else:
                detalle = str(exc)
            errores.append(f"{trabajador}: {detalle}")
    return ok, errores


def validar(liquidacion, usuario=None):
    liquidacion.periodo.assert_editable()
    if liquidacion.requiere_recalculo:
        raise ValidationError(
            "Hay que recalcular la liquidación antes de validarla."
        )
    if liquidacion.estado != LiquidacionMensual.Estado.CALCULADA:
        raise ValidationError("Solo se valida una liquidación calculada.")
    liquidacion.estado = LiquidacionMensual.Estado.VALIDADA
    if usuario is not None:
        liquidacion.actualizado_por = usuario
    liquidacion.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
    return liquidacion


def anular(liquidacion, usuario=None):
    liquidacion.periodo.assert_editable()
    if liquidacion.estado == LiquidacionMensual.Estado.ANULADA:
        raise ValidationError("La liquidación ya está anulada.")
    if liquidacion.estado == LiquidacionMensual.Estado.CERRADA:
        raise ValidationError("Una liquidación cerrada no se anula.")
    from remuneraciones.services.costos import eliminar_si_existe

    eliminar_si_existe(liquidacion)
    liquidacion.estado = LiquidacionMensual.Estado.ANULADA
    if usuario is not None:
        liquidacion.actualizado_por = usuario
    liquidacion.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
    return liquidacion


def marcar_pagada(liquidacion, usuario=None):
    """PAGADA solo si existe PagoRemuneracion; no por un total copiado de Excel."""
    liquidacion.periodo.assert_editable()
    if liquidacion.estado != LiquidacionMensual.Estado.VALIDADA:
        raise ValidationError("Solo se marca pagada una liquidación validada.")
    if liquidacion.total_pagado <= 0:
        raise ValidationError(
            "Debe registrar al menos un pago antes de marcar la liquidación "
            "como pagada."
        )
    liquidacion.estado = LiquidacionMensual.Estado.PAGADA
    if usuario is not None:
        liquidacion.actualizado_por = usuario
    liquidacion.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
    return liquidacion


def registrar_pago(
    liquidacion,
    *,
    fecha,
    monto,
    medio_pago=PagoRemuneracion.MedioPago.TRANSFERENCIA,
    referencia="",
    observaciones="",
    usuario=None,
):
    liquidacion.periodo.assert_editable()
    if liquidacion.estado in (
        LiquidacionMensual.Estado.ANULADA,
        LiquidacionMensual.Estado.CERRADA,
        LiquidacionMensual.Estado.BORRADOR,
    ):
        raise ValidationError(
            "No se registran pagos en una liquidación "
            f"{liquidacion.get_estado_display().lower()}."
        )
    pago = PagoRemuneracion(
        liquidacion=liquidacion,
        fecha=fecha,
        monto=dinero(monto),
        medio_pago=medio_pago,
        referencia=referencia or "",
        observaciones=observaciones or "",
        creado_por=usuario,
        actualizado_por=usuario,
    )
    pago.full_clean()
    pago.save()
    return pago


def acciones_disponibles(liquidacion):
    cerrado = liquidacion.periodo.esta_cerrado
    return {
        "calcular": (
            not cerrado
            and liquidacion.estado
            not in (
                LiquidacionMensual.Estado.PAGADA,
                LiquidacionMensual.Estado.CERRADA,
                LiquidacionMensual.Estado.ANULADA,
            )
        ),
        "validar": (
            not cerrado
            and liquidacion.estado == LiquidacionMensual.Estado.CALCULADA
            and not liquidacion.requiere_recalculo
        ),
        "pagar": (
            not cerrado
            and liquidacion.estado == LiquidacionMensual.Estado.VALIDADA
        ),
        "anular": (
            not cerrado
            and liquidacion.estado
            not in (
                LiquidacionMensual.Estado.ANULADA,
                LiquidacionMensual.Estado.CERRADA,
            )
        ),
        "pago": (
            not cerrado
            and liquidacion.estado
            in (
                LiquidacionMensual.Estado.CALCULADA,
                LiquidacionMensual.Estado.VALIDADA,
                LiquidacionMensual.Estado.PAGADA,
            )
        ),
    }
