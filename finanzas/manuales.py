from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finanzas.models import CategoriaFinanciera, MovimientoFinanciero


@transaction.atomic
def registrar_movimiento_manual(movimiento):
    categoria = movimiento.categoria
    if movimiento.origen != MovimientoFinanciero.Origen.MANUAL:
        raise ValidationError("FIN005 solo registra movimientos con origen MANUAL.")
    if not categoria.activo or not categoria.permite_manual:
        raise ValidationError("La categoría seleccionada no permite movimientos manuales.")
    if movimiento.tipo != categoria.tipo:
        raise ValidationError("La naturaleza no coincide con la categoría.")
    if movimiento.monto <= 0:
        raise ValidationError("El monto debe ser mayor que cero.")
    movimiento.full_clean()
    movimiento.save()
    return movimiento


@transaction.atomic
def anular_movimiento_manual(movimiento, usuario, motivo):
    if movimiento.origen != MovimientoFinanciero.Origen.MANUAL:
        raise ValidationError("Solo se pueden anular movimientos manuales desde FIN005.")
    if movimiento.anulado:
        raise ValidationError("El movimiento ya está anulado.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo de anulación es obligatorio.")
    movimiento.anulado = True
    movimiento.anulado_en = timezone.now()
    movimiento.anulado_por = usuario
    movimiento.motivo_anulacion = motivo
    movimiento.save(update_fields=["anulado", "anulado_en", "anulado_por", "motivo_anulacion", "actualizado_en"])
    return movimiento
