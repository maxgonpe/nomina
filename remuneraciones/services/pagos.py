"""
REM005-C01 — Control, anulación y corrección de pagos de remuneración.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from remuneraciones.models import LiquidacionMensual, PagoRemuneracion
from remuneraciones.services.movimientos import dinero


def _format_clp(valor):
    monto = dinero(valor)
    entero, frac = f"{monto:.2f}".split(".")
    miles = "{:,}".format(int(entero)).replace(",", ".")
    return f"${miles},{frac}"


def total_pagado_vigente(liquidacion):
    total = liquidacion.pagos.filter(anulado=False).aggregate(
        total=Sum("monto")
    )["total"]
    return dinero(total or Decimal("0.00"))


def saldo_pendiente(liquidacion):
    return dinero(liquidacion.total_a_pagar or 0) - total_pagado_vigente(
        liquidacion
    )


def _validar_liquidacion_para_pago(liquidacion):
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


def _mensaje_sobrepago(monto, saldo):
    monto_pago = dinero(monto)
    saldo_actual = dinero(saldo)
    exceso = dinero(monto_pago - saldo_actual)
    return (
        "No se puede registrar el pago. "
        f"Monto ingresado: {_format_clp(monto_pago)} "
        f"Saldo pendiente: {_format_clp(saldo_actual)}. "
        f"El monto excede el saldo pendiente en {_format_clp(exceso)}."
    )


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
    _validar_liquidacion_para_pago(liquidacion)
    monto_pago = dinero(monto)
    if monto_pago <= 0:
        raise ValidationError("El monto del pago debe ser mayor que 0.")
    saldo = saldo_pendiente(liquidacion)
    if monto_pago > saldo:
        raise ValidationError(_mensaje_sobrepago(monto_pago, saldo))
    pago = PagoRemuneracion(
        liquidacion=liquidacion,
        fecha=fecha,
        monto=monto_pago,
        medio_pago=medio_pago,
        referencia=referencia or "",
        observaciones=observaciones or "",
        creado_por=usuario,
        actualizado_por=usuario,
    )
    pago.full_clean()
    pago.save()
    return pago


@transaction.atomic
def anular_pago(pago, *, motivo, usuario=None):
    if pago.anulado:
        raise ValidationError("El pago ya está anulado.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("Debe indicar el motivo de anulación.")
    liquidacion = pago.liquidacion
    liquidacion.periodo.assert_editable()
    pago.anulado = True
    pago.motivo_anulacion = motivo
    pago.anulado_en = timezone.now()
    pago.anulado_por = usuario
    pago.actualizado_por = usuario
    pago.save(
        update_fields=[
            "anulado",
            "motivo_anulacion",
            "anulado_en",
            "anulado_por",
            "actualizado_por",
            "actualizado_en",
        ]
    )
    actualizar_estado_liquidacion(liquidacion, usuario=usuario)
    return pago


def actualizar_estado_liquidacion(liquidacion, usuario=None):
    """Si estaba PAGADA y queda saldo, vuelve a VALIDADA."""
    if liquidacion.estado != LiquidacionMensual.Estado.PAGADA:
        return liquidacion
    if liquidacion.saldo_pendiente != Decimal("0.00"):
        liquidacion.estado = LiquidacionMensual.Estado.VALIDADA
        if usuario is not None:
            liquidacion.actualizado_por = usuario
        liquidacion.save(
            update_fields=["estado", "actualizado_por", "actualizado_en"]
        )
    return liquidacion
