from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from facturacion.models import DocumentoTributario


def actualizar_estado(documento):
    if documento.estado == DocumentoTributario.Estado.ANULADA:
        return documento
    total = documento.total_cobrado
    estado = DocumentoTributario.Estado.EMITIDA if total == 0 else DocumentoTributario.Estado.PAGADA if total == documento.total else DocumentoTributario.Estado.PARCIAL
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


@transaction.atomic
def anular_cobro(cobro, *, motivo, usuario=None):
    if cobro.anulado:
        raise ValidationError("El cobro ya está anulado.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo de anulación es obligatorio.")
    cobro.anulado = True
    cobro.anulado_en = timezone.now()
    cobro.anulado_por = usuario
    cobro.motivo_anulacion = motivo
    cobro.actualizado_por = usuario
    cobro.save(update_fields=["anulado", "anulado_en", "anulado_por", "motivo_anulacion", "actualizado_por", "actualizado_en"])
    actualizar_estado(cobro.documento)
    return cobro
