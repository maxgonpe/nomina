from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finanzas.models import CategoriaFinanciera, MovimientoFinanciero, ObligacionFinanciera, PagoObligacionFinanciera


def total_pagado(obligacion, fecha_corte=None):
    pagos = obligacion.pagos.filter(anulado=False)
    if fecha_corte:
        pagos = pagos.filter(fecha__lte=fecha_corte)
    return sum((p.monto for p in pagos), Decimal("0.00"))


def saldo(obligacion, fecha_corte=None):
    return obligacion.monto_total - total_pagado(obligacion, fecha_corte)


def situacion(obligacion):
    if obligacion.estado == ObligacionFinanciera.Estado.ANULADA:
        return obligacion.estado
    restante = saldo(obligacion)
    if restante <= 0:
        return ObligacionFinanciera.Estado.PAGADA
    if total_pagado(obligacion) > 0:
        return ObligacionFinanciera.Estado.PARCIAL
    return ObligacionFinanciera.Estado.PENDIENTE


@transaction.atomic
def registrar_pago(pago):
    if pago.obligacion.estado == ObligacionFinanciera.Estado.ANULADA:
        raise ValidationError("No se puede pagar una obligación anulada.")
    if pago.monto <= 0:
        raise ValidationError("El pago debe ser mayor que cero.")
    if pago.monto > saldo(pago.obligacion):
        raise ValidationError("El pago supera el saldo pendiente.")
    pago.full_clean()
    pago.save()
    pago.obligacion.estado = situacion(pago.obligacion)
    pago.obligacion.save(update_fields=["estado", "actualizado_en"])
    sincronizar_pago_obligacion(pago)
    return pago


@transaction.atomic
def anular_pago(pago, usuario, motivo):
    if pago.anulado:
        raise ValidationError("El pago ya está anulado.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo de anulación es obligatorio.")
    pago.anulado = True
    pago.anulado_en = timezone.now()
    pago.anulado_por = usuario
    pago.motivo_anulacion = motivo
    pago.save(update_fields=["anulado", "anulado_en", "anulado_por", "motivo_anulacion", "actualizado_en"])
    MovimientoFinanciero.objects.filter(origen=MovimientoFinanciero.Origen.OTRO, referencia=f"OBLIGACION_PAGO:{pago.pk}").update(anulado=True, anulado_en=timezone.now(), anulado_por=usuario, motivo_anulacion=motivo)
    pago.obligacion.estado = situacion(pago.obligacion)
    pago.obligacion.save(update_fields=["estado", "actualizado_en"])
    return pago


@transaction.atomic
def sincronizar_pago_obligacion(pago):
    if pago.anulado:
        return None
    movimiento, _ = MovimientoFinanciero.objects.update_or_create(
        origen=MovimientoFinanciero.Origen.OTRO,
        referencia=f"OBLIGACION_PAGO:{pago.pk}",
        defaults={"fecha": pago.fecha, "tipo": MovimientoFinanciero.Tipo.EGRESO, "categoria": pago.obligacion.categoria, "centro_costo": pago.obligacion.centro_costo, "descripcion": f"Pago obligación {pago.obligacion.descripcion}", "monto": pago.monto, "observaciones": pago.observaciones},
    )
    return movimiento


def obligaciones_pendientes(fecha_corte=None):
    obligaciones = ObligacionFinanciera.objects.exclude(estado=ObligacionFinanciera.Estado.ANULADA)
    return [o for o in obligaciones if saldo(o, fecha_corte) > 0]
