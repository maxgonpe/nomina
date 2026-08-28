from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from impuestos.models import PeriodoImpuesto, PagoImpuesto


def situacion_pago(periodo):
    if periodo.monto_a_pagar == 0:
        return "SIN_PAGO_REQUERIDO"
    if periodo.total_pagado == 0:
        return "PENDIENTE"
    if periodo.total_pagado < periodo.monto_a_pagar:
        return "PARCIAL"
    return "PAGADO"


@transaction.atomic
def registrar_pago(pago):
    periodo = PeriodoImpuesto.objects.select_for_update().get(pk=pago.periodo_id)
    if periodo.estado not in (PeriodoImpuesto.Estado.VALIDADO, PeriodoImpuesto.Estado.CERRADO, PeriodoImpuesto.Estado.DECLARADO, PeriodoImpuesto.Estado.PAGADO):
        raise ValidationError("El período debe estar validado antes de registrar pagos.")
    if pago.monto <= 0 or periodo.total_pagado + pago.monto > periodo.monto_a_pagar:
        raise ValidationError("El pago supera el saldo pendiente del período.")
    pago.full_clean()
    pago.save()
    return pago


@transaction.atomic
def anular_pago(pago, usuario, motivo):
    motivo = (motivo or "").strip()
    if pago.anulado:
        raise ValidationError("El pago ya está anulado.")
    if not motivo:
        raise ValidationError("El motivo de anulación es obligatorio.")
    pago.anulado = True
    pago.anulado_en = timezone.now()
    pago.anulado_por = usuario
    pago.motivo_anulacion = motivo
    pago.save(update_fields=["anulado", "anulado_en", "anulado_por", "motivo_anulacion", "actualizado_en"])
    return pago
