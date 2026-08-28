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


def anular_documento_compra(documento):
    if documento.estado == DocumentoCompra.Estado.ANULADO:
        raise ValidationError("El documento ya está anulado.")
    documento.estado = DocumentoCompra.Estado.ANULADO
    documento.save(update_fields=["estado", "actualizado_en"])
    return documento
