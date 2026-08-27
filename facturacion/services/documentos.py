from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction

from core.services.parametros import valor
from facturacion.models import DocumentoTributario

TASA_IVA = "TASA_IVA"
CENTAVO = Decimal("0.01")


def calcular_documento(fecha_emision, tipo_documento, neto):
    """Calcula y devuelve los importes oficiales, sin tocar el documento."""
    if neto is None or neto < 0:
        raise ValidationError("El neto no puede ser negativo.")
    neto = Decimal(neto)
    if tipo_documento == DocumentoTributario.Tipo.FACTURA_EXENTA:
        tasa = Decimal("0")
        iva = Decimal("0.00")
    else:
        tasa = valor(TASA_IVA, fecha_emision)
        iva = (neto * tasa).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return {
        "tasa_iva_snapshot": tasa,
        "iva": iva,
        "total": neto + iva,
    }


@transaction.atomic
def registrar_documento(documento):
    importes = calcular_documento(documento.fecha_emision, documento.tipo_documento, documento.neto)
    for campo, importe in importes.items():
        setattr(documento, campo, importe)
    documento.full_clean()
    documento.save()
    return documento


@transaction.atomic
def recalcular_documento(documento):
    if documento.estado != DocumentoTributario.Estado.EMITIDA:
        raise ValidationError("Solo se pueden recalcular documentos emitidos.")
    if documento.total_cobrado > 0:
        raise ValidationError("No se puede recalcular un documento con cobros.")
    return registrar_documento(documento)


@transaction.atomic
def anular_documento(documento):
    if documento.estado == DocumentoTributario.Estado.ANULADA:
        raise ValidationError("El documento ya está anulado.")
    documento.estado = DocumentoTributario.Estado.ANULADA
    documento.save(update_fields=["estado", "actualizado_en"])
    return documento
