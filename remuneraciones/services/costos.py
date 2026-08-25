from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from remuneraciones.models import (
    ConceptoCostoTrabajador,
    CostoTrabajadorDetalle,
    CostoTrabajadorPeriodo,
    LiquidacionMensual,
)
from remuneraciones.services.movimientos import dinero

CODIGO_TOTAL_LIQUIDADO = "TOTAL_LIQUIDADO"

ESTADOS_LIQUIDACION_OK = {
    LiquidacionMensual.Estado.CALCULADA,
    LiquidacionMensual.Estado.VALIDADA,
    LiquidacionMensual.Estado.PAGADA,
    LiquidacionMensual.Estado.CERRADA,
}


def generar_desde_liquidacion(liquidacion, usuario=None):
    """
    Genera o regenera el costo del trabajador a partir de una liquidación
    calculada. Snapshot de CC y días desde la liquidación; montos desde
    movimientos según el catálogo configurable de ConceptoCostoTrabajador.
    """
    liquidacion.periodo.assert_editable()
    if liquidacion.estado == LiquidacionMensual.Estado.ANULADA:
        raise ValidationError(
            "No se genera costo desde una liquidación anulada."
        )
    if liquidacion.estado == LiquidacionMensual.Estado.BORRADOR:
        raise ValidationError(
            "La liquidación debe estar calculada antes de generar el costo."
        )
    if liquidacion.estado not in ESTADOS_LIQUIDACION_OK:
        raise ValidationError(
            "La liquidación no está en un estado válido para generar costo."
        )
    if liquidacion.requiere_recalculo:
        raise ValidationError(
            "Hay que recalcular la liquidación antes de generar el costo."
        )

    conceptos = list(
        ConceptoCostoTrabajador.objects.filter(activo=True).order_by(
            "orden", "codigo"
        )
    )
    if not conceptos:
        raise ValidationError(
            "No hay conceptos de costo activos. Revise el catálogo REM009."
        )

    montos_por_origen = {
        row["concepto__codigo"]: dinero(row["total"] or 0)
        for row in liquidacion.movimientos.values("concepto__codigo").annotate(
            total=Sum("monto")
        )
    }

    with transaction.atomic():
        costo, _creado = CostoTrabajadorPeriodo.objects.select_for_update().get_or_create(
            liquidacion=liquidacion,
            defaults={
                "creado_por": usuario,
                "actualizado_por": usuario,
            },
        )
        centro = liquidacion.centro_costo
        costo.centro_costo = centro
        costo.centro_costo_codigo_snapshot = (
            liquidacion.centro_costo_codigo_snapshot
            or (getattr(centro, "codigo", "") or "")
        )
        costo.centro_costo_nombre_snapshot = (
            liquidacion.centro_costo_nombre_snapshot
            or (getattr(centro, "nombre", "") or "")
        )
        costo.dias_trabajados = liquidacion.dias_trabajados
        if usuario is not None:
            costo.actualizado_por = usuario

        existentes = {
            d.concepto_id: d
            for d in costo.detalles.select_related("concepto")
        }
        total = Decimal("0.00")
        vistos = set()
        for concepto in conceptos:
            if concepto.codigo == CODIGO_TOTAL_LIQUIDADO or not concepto.codigo_origen:
                monto = dinero(liquidacion.total_liquidado)
                obs = "Referencia: total liquidado de la liquidación"
            else:
                monto = montos_por_origen.get(
                    concepto.codigo_origen, Decimal("0.00")
                )
                obs = (
                    f"Desde concepto {concepto.codigo_origen}"
                    if monto
                    else f"Sin movimiento {concepto.codigo_origen}"
                )
            detalle = existentes.get(concepto.pk)
            if detalle is None:
                detalle = CostoTrabajadorDetalle(
                    costo_trabajador=costo,
                    concepto=concepto,
                    creado_por=usuario,
                )
            detalle.monto = monto
            detalle.observaciones = obs
            if usuario is not None:
                detalle.actualizado_por = usuario
            detalle.full_clean()
            detalle.save()
            vistos.add(concepto.pk)
            if concepto.incluye_en_total:
                total += monto

        for concepto_id, detalle in existentes.items():
            if concepto_id not in vistos:
                CostoTrabajadorDetalle.objects.filter(pk=detalle.pk).delete()

        costo.total = dinero(total)
        costo.calculado_en = timezone.now()
        costo.save()
    costo.refresh_from_db()
    return costo


def generar_periodo(periodo, usuario=None):
    """Genera costos para todas las liquidaciones calculadas del período."""
    periodo.assert_editable()
    ok = []
    errores = []
    qs = (
        LiquidacionMensual.objects.filter(periodo=periodo)
        .exclude(estado=LiquidacionMensual.Estado.ANULADA)
        .exclude(estado=LiquidacionMensual.Estado.BORRADOR)
        .select_related("trabajador", "periodo", "centro_costo")
        .order_by("trabajador__nombre_completo")
    )
    for liquidacion in qs:
        try:
            ok.append(generar_desde_liquidacion(liquidacion, usuario=usuario))
        except ValidationError as exc:
            if hasattr(exc, "messages"):
                detalle = " ".join(str(m) for m in exc.messages)
            else:
                detalle = str(exc)
            errores.append(f"{liquidacion.trabajador}: {detalle}")
    return ok, errores


def eliminar_si_existe(liquidacion):
    CostoTrabajadorPeriodo.objects.filter(liquidacion=liquidacion).delete()


def totales_por_centro(periodo):
    """Suma de costos por centro de costo (insumo futuro de finanzas)."""
    return (
        CostoTrabajadorPeriodo.objects.filter(liquidacion__periodo=periodo)
        .exclude(
            liquidacion__estado=LiquidacionMensual.Estado.ANULADA,
        )
        .values(
            "centro_costo_codigo_snapshot",
            "centro_costo_nombre_snapshot",
        )
        .annotate(total=Sum("total"))
        .order_by("centro_costo_codigo_snapshot")
    )
