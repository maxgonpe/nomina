from calendar import monthrange
from datetime import date
from facturacion.models import DocumentoTributario


def _rango(anio, mes):
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


def datos_impuestos(documento):
    """Salida normalizada para IVA ventas, basada en la fecha de emisión."""
    if documento.estado == DocumentoTributario.Estado.ANULADA:
        return None
    return {
        "documento_id": documento.pk,
        "fecha_emision": documento.fecha_emision,
        "tipo": documento.tipo_documento,
        "neto": documento.neto,
        "iva": documento.iva,
        "total": documento.total,
        "estado": documento.estado,
    }


def documentos_impuestos(anio, mes):
    inicio, fin = _rango(anio, mes)
    return [datos_impuestos(d) for d in DocumentoTributario.objects.select_related("cliente", "obra").filter(fecha_emision__range=(inicio, fin)).exclude(estado=DocumentoTributario.Estado.ANULADA)]


def datos_financieros(documento):
    """Una fila por cobro: el período financiero es la fecha efectiva del cobro."""
    if documento.estado == DocumentoTributario.Estado.ANULADA:
        return []
    return [{
        "documento_id": documento.pk,
        "cliente": documento.cliente,
        "obra": documento.obra,
        "centro_costo": documento.obra.centro_costo if documento.obra else None,
        "fecha": cobro.fecha,
        "monto": cobro.monto,
        "cobrado": cobro.monto,
        "saldo": documento.saldo_pendiente,
    } for cobro in documento.cobros.all()]


def cobros_financieros(anio, mes):
    inicio, fin = _rango(anio, mes)
    documentos = DocumentoTributario.objects.select_related("cliente", "obra", "obra__centro_costo").prefetch_related("cobros").exclude(estado=DocumentoTributario.Estado.ANULADA).filter(cobros__fecha__range=(inicio, fin)).distinct()
    return [fila for documento in documentos for fila in datos_financieros(documento) if inicio <= fila["fecha"] <= fin]


def filas_excel(documentos=None):
    """Reconstruye la fila de facturación sin usar el PK como ITEM."""
    if documentos is None:
        documentos = DocumentoTributario.objects.select_related("cliente", "obra").exclude(estado=DocumentoTributario.Estado.ANULADA).order_by("fecha_emision", "pk")
    filas = []
    for item, documento in enumerate(documentos, start=1):
        filas.append({
            "item": item,
            "emision": documento.fecha_emision,
            "rut_cliente": documento.cliente.rut,
            "cliente": documento.cliente.razon_social,
            "obra": documento.obra.nombre if documento.obra else "",
            "tipo_documento": documento.tipo_documento,
            "neto": documento.neto,
            "iva": documento.iva,
            "total": documento.total,
            "numero": documento.numero,
            "estado": documento.estado,
        })
    return filas
