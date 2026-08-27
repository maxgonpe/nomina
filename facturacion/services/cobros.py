from django.core.exceptions import ValidationError
from django.db import transaction

from facturacion.models import DocumentoTributario


def actualizar_estado(documento):
    if documento.estado == DocumentoTributario.Estado.ANULADA:
        return documento
    total = documento.total_cobrado
    if total == 0:
        estado = DocumentoTributario.Estado.EMITIDA
    elif total < documento.total:
        estado = DocumentoTributario.Estado.PARCIAL
    else:
        estado = DocumentoTributario.Estado.PAGADA
    if documento.estado != estado:
        documento.estado = estado
        documento.save(update_fields=["estado", "actualizado_en"])
    return documento


@transaction.atomic
def registrar_cobro(cobro):
    documento = DocumentoTributario.objects.select_for_update().get(pk=cobro.documento_id)
    if documento.estado == DocumentoTributario.Estado.ANULADA:
        raise ValidationError("No se pueden registrar cobros para un documento anulado.")
    if cobro.monto <= 0 or documento.total_cobrado + cobro.monto > documento.total:
        raise ValidationError("El cobro supera el saldo pendiente del documento.")
    cobro.full_clean()
    cobro.save()
    actualizar_estado(documento)
    return cobro
