from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from remuneraciones.models import (
    ConceptoRemuneracion,
    Finiquito,
    LiquidacionMensual,
    MovimientoRemuneracion,
    marcar_liquidacion_pendiente_recalculo,
)
from remuneraciones.services.movimientos import (
    dinero,
    obtener_o_crear_liquidacion_borrador,
)
from rrhh.services.contratos import terminar_contrato as cerrar_contrato

CODIGO_FINIQUITO = "FINIQUITO"


def concepto_finiquito():
    try:
        return ConceptoRemuneracion.objects.get(codigo=CODIGO_FINIQUITO)
    except ConceptoRemuneracion.DoesNotExist as exc:
        raise ValidationError(
            "Falta el concepto FINIQUITO en el catálogo (REM004)."
        ) from exc


def finiquitos_activos(trabajador, periodo):
    return Finiquito.objects.filter(
        trabajador=trabajador,
        periodo=periodo,
    ).exclude(estado=Finiquito.Estado.ANULADO)


def suma_finiquitos(trabajador, periodo):
    """
    Insumo de REM005: monto del evento de finiquito (validado o pagado).
    No usar la columna Excel ni un movimiento suelto como fuente.
    """
    total = (
        Finiquito.objects.filter(
            trabajador=trabajador,
            periodo=periodo,
            estado__in=[
                Finiquito.Estado.VALIDADO,
                Finiquito.Estado.PAGADO,
            ],
        ).aggregate(total=Sum("monto"))["total"]
    )
    return total or Decimal("0.00")


def _movimiento_finiquito(liquidacion):
    return (
        MovimientoRemuneracion.objects.filter(
            liquidacion=liquidacion,
            concepto__codigo=CODIGO_FINIQUITO,
            origen=MovimientoRemuneracion.Origen.CALCULADO,
        )
        .order_by("id")
        .first()
    )


def sincronizar_movimiento_finiquito(finiquito, usuario=None):
    """
    Refleja el finiquito validado en la liquidación con un solo movimiento
    FINIQUITO. Si REM005 vuelve a calcular, llama esta función: actualiza
    el mismo registro, no crea otro.
    """
    if not finiquito.alimenta_liquidacion:
        quitar_movimiento_finiquito(finiquito)
        return None

    concepto = concepto_finiquito()
    liquidacion = obtener_o_crear_liquidacion_borrador(
        finiquito.trabajador,
        finiquito.periodo,
        usuario=usuario,
    )
    monto = dinero(finiquito.monto)
    descripcion = (
        f"Finiquito {finiquito.fecha.isoformat()} "
        f"({finiquito.get_motivo_display() or 'sin motivo'})"
    )
    movimiento = _movimiento_finiquito(liquidacion)
    if movimiento:
        MovimientoRemuneracion.objects.filter(pk=movimiento.pk).update(
            monto=monto,
            descripcion=descripcion,
            generado_automaticamente=True,
            bloqueado=True,
            actualizado_por=usuario,
        )
        marcar_liquidacion_pendiente_recalculo(
            liquidacion.trabajador_id,
            liquidacion.periodo_id,
        )
        movimiento.refresh_from_db()
    else:
        movimiento = MovimientoRemuneracion(
            liquidacion=liquidacion,
            concepto=concepto,
            monto=monto,
            origen=MovimientoRemuneracion.Origen.CALCULADO,
            descripcion=descripcion,
            generado_automaticamente=True,
            bloqueado=True,
            creado_por=usuario,
            actualizado_por=usuario,
        )
        movimiento.full_clean()
        movimiento.save()
    Finiquito.objects.filter(pk=finiquito.pk).update(liquidacion=liquidacion)
    finiquito.liquidacion = liquidacion
    return movimiento


def quitar_movimiento_finiquito(finiquito):
    liquidacion = finiquito.liquidacion
    if liquidacion is None:
        liquidacion = LiquidacionMensual.objects.filter(
            trabajador=finiquito.trabajador,
            periodo=finiquito.periodo,
        ).first()
    if liquidacion is None:
        return
    liquidacion.periodo.assert_editable()
    qs = MovimientoRemuneracion.objects.filter(
        liquidacion=liquidacion,
        concepto__codigo=CODIGO_FINIQUITO,
        origen=MovimientoRemuneracion.Origen.CALCULADO,
    )
    if qs.exists():
        qs.delete()
        marcar_liquidacion_pendiente_recalculo(
            liquidacion.trabajador_id,
            liquidacion.periodo_id,
        )


def registrar(
    *,
    trabajador,
    contrato,
    periodo,
    fecha,
    monto,
    motivo="",
    observaciones="",
    archivo=None,
    usuario=None,
    instance=None,
):
    """Alta o edición en borrador. No alimenta liquidación ni cierra contrato."""
    periodo.assert_editable()
    finiquito = instance if instance is not None and instance.pk else Finiquito()
    if finiquito.pk and finiquito.estado != Finiquito.Estado.BORRADOR:
        raise ValidationError(
            "Solo se editan fecha, contrato y monto en un finiquito en borrador."
        )
    finiquito.trabajador = trabajador
    finiquito.contrato = contrato
    finiquito.periodo = periodo
    finiquito.fecha = fecha
    finiquito.monto = dinero(monto)
    finiquito.motivo = motivo or Finiquito.Motivo.OTRO
    finiquito.observaciones = observaciones or ""
    if archivo:
        finiquito.archivo = archivo
    finiquito.estado = Finiquito.Estado.BORRADOR
    if usuario is not None:
        if not finiquito.pk:
            finiquito.creado_por = usuario
        finiquito.actualizado_por = usuario
    otros = finiquitos_activos(trabajador, periodo)
    if finiquito.pk:
        otros = otros.exclude(pk=finiquito.pk)
    if otros.exists():
        raise ValidationError(
            "Ya hay un finiquito activo de este trabajador en el período."
        )
    finiquito.full_clean()
    finiquito.save()
    return finiquito


def actualizar_documento(finiquito, *, archivo=None, observaciones=None, usuario=None):
    """Adjunto y notas: se pueden completar después de validar (trazabilidad)."""
    finiquito.periodo.assert_editable()
    if finiquito.estado == Finiquito.Estado.ANULADO:
        raise ValidationError("Un finiquito anulado no se puede modificar.")
    if observaciones is not None:
        finiquito.observaciones = observaciones
    if archivo is not None:
        finiquito.archivo = archivo
    if usuario is not None:
        finiquito.actualizado_por = usuario
    finiquito.save(update_fields=["observaciones", "archivo", "actualizado_por", "actualizado_en"])
    return finiquito


def validar(finiquito, usuario=None):
    """Pasa a VALIDADO y genera (o actualiza) el movimiento FINIQUITO."""
    finiquito.periodo.assert_editable()
    if finiquito.estado != Finiquito.Estado.BORRADOR:
        raise ValidationError("Solo se valida un finiquito en borrador.")
    with transaction.atomic():
        finiquito.estado = Finiquito.Estado.VALIDADO
        if usuario is not None:
            finiquito.actualizado_por = usuario
        finiquito.full_clean()
        finiquito.save()
        sincronizar_movimiento_finiquito(finiquito, usuario=usuario)
    finiquito.refresh_from_db()
    return finiquito


def pagar(finiquito, usuario=None):
    finiquito.periodo.assert_editable()
    if finiquito.estado != Finiquito.Estado.VALIDADO:
        raise ValidationError("Solo se marca pagado un finiquito validado.")
    finiquito.estado = Finiquito.Estado.PAGADO
    if usuario is not None:
        finiquito.actualizado_por = usuario
    finiquito.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
    return finiquito


def anular(finiquito, usuario=None):
    """Conserva el evento. Quita el movimiento para que REM005 no lo duplique ni lo sume."""
    finiquito.periodo.assert_editable()
    if finiquito.estado == Finiquito.Estado.ANULADO:
        raise ValidationError("El finiquito ya está anulado.")
    with transaction.atomic():
        finiquito.estado = Finiquito.Estado.ANULADO
        if usuario is not None:
            finiquito.actualizado_por = usuario
        finiquito.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
        quitar_movimiento_finiquito(finiquito)
    finiquito.refresh_from_db()
    return finiquito


def terminar_contrato_por_finiquito(finiquito, usuario=None):
    """
    Acción explícita de UI/servicio. Validar el finiquito no cierra el contrato.
    """
    if finiquito.estado not in (
        Finiquito.Estado.VALIDADO,
        Finiquito.Estado.PAGADO,
    ):
        raise ValidationError(
            "Valide el finiquito antes de cerrar el contrato."
        )
    return cerrar_contrato(
        finiquito.contrato,
        finiquito.fecha,
        usuario=usuario,
    )


def acciones_disponibles(finiquito):
    if finiquito.periodo.esta_cerrado or finiquito.esta_anulado:
        return {
            "validar": False,
            "pagar": False,
            "anular": False,
            "terminar_contrato": False,
            "editar": False,
            "borrar": False,
        }
    contrato_abierto = finiquito.contrato.estado != finiquito.contrato.Estado.TERMINADO
    return {
        "validar": finiquito.estado == Finiquito.Estado.BORRADOR,
        "pagar": finiquito.estado == Finiquito.Estado.VALIDADO,
        "anular": finiquito.estado != Finiquito.Estado.ANULADO,
        "terminar_contrato": (
            finiquito.estado in (
                Finiquito.Estado.VALIDADO,
                Finiquito.Estado.PAGADO,
            )
            and contrato_abierto
        ),
        "editar": True,
        "borrar": finiquito.estado == Finiquito.Estado.BORRADOR,
    }
