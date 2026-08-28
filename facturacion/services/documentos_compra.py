from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError
from core.services.parametros import valor
from facturacion.models import DocumentoCompra


def calcular_documento_compra(fecha, tipo, neto):
    if neto is None or neto < 0:
        raise ValidationError("El neto no puede ser negativo.")
    neto = Decimal(neto)
    if "EXENTA" in (tipo or "").upper():
        tasa, iva = Decimal("0"), Decimal("0.00")
    else:
        tasa = valor("TASA_IVA", fecha)
        iva = (neto * tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"tasa_iva_snapshot": tasa, "iva": iva, "total": neto + iva}


def anular_documento_compra(documento, *, usuario=None, motivo_anulacion=""):
    if documento.estado == DocumentoCompra.Estado.ANULADO:
        raise ValidationError("El documento ya está anulado.")
    if documento.total_pagado > 0:
        raise ValidationError("No se puede anular un documento con pagos registrados.")
    motivo_anulacion = (motivo_anulacion or "").strip()
    if not motivo_anulacion:
        raise ValidationError("El motivo de anulación es obligatorio.")
    documento.estado = DocumentoCompra.Estado.ANULADO
    documento.observaciones = f"{documento.observaciones}\nAnulación: {motivo_anulacion}".strip()
    documento.actualizado_por = usuario
    documento.save(update_fields=["estado", "observaciones", "actualizado_por", "actualizado_en"])
    return documento
