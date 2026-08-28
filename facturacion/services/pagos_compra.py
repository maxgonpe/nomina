from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from facturacion.models import DocumentoCompra, PagoDocumentoCompra


def actualizar_estado(documento):
    if documento.estado == DocumentoCompra.Estado.ANULADO:
        return documento
    pagado = documento.total_pagado
    if pagado == 0:
        estado = DocumentoCompra.Estado.REGISTRADO
    elif pagado < documento.total:
        estado = DocumentoCompra.Estado.PARCIAL
    else:
        estado = DocumentoCompra.Estado.PAGADO
    if documento.estado != estado:
        documento.estado = estado
        documento.save(update_fields=["estado", "actualizado_en"])
    return documento


@transaction.atomic
def registrar_pago(pago):
    documento = DocumentoCompra.objects.select_for_update().get(pk=pago.documento_id)
    if documento.estado == DocumentoCompra.Estado.ANULADO:
        raise ValidationError("No se pueden registrar pagos para un documento anulado.")
    otros = documento.total_pagado
    if pago.pk and not pago.anulado:
        otros -= pago.monto
    if pago.monto <= 0 or otros + pago.monto > documento.total:
        raise ValidationError("El pago supera el saldo pendiente del documento.")
    pago.full_clean()
    pago.save()
    actualizar_estado(documento)
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
    actualizar_estado(pago.documento)
    return pago
