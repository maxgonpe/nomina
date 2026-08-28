from facturacion.models import DocumentoCompra, PagoDocumentoCompra
from facturacion.services.iva_compras import documentos_del_periodo, _signo
from facturacion.services.reportes_compras import filas_exportacion_compras as _filas_compras


def documentos_para_impuestos(fecha_desde=None, fecha_hasta=None):
    """Entrega hechos documentales, sin mezclar pagos ni reglas de IMP."""
    salida = []
    for documento in documentos_del_periodo(fecha_desde, fecha_hasta):
        signo = _signo(documento)
        salida.append({
            "documento_id": documento.pk,
            "proveedor": documento.proveedor,
            "rut_proveedor": documento.proveedor.rut,
            "tipo": documento.tipo_documento,
            "numero": documento.numero,
            "fecha_documento": documento.fecha_documento,
            "fecha_recepcion": documento.fecha_recepcion,
            "neto": documento.neto * signo,
            "tasa_iva_snapshot": documento.tasa_iva_snapshot,
            "iva": documento.iva * signo,
            "total": documento.total * signo,
            "centro_costo": documento.centro_costo,
            "estado": documento.estado,
            "anulado": False,
            "signo": signo,
        })
    return salida


def pagos_para_finanzas(fecha_desde=None, fecha_hasta=None):
    qs = PagoDocumentoCompra.objects.select_related("documento__proveedor", "documento__centro_costo").filter(anulado=False)
    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lte=fecha_hasta)
    return [{
        "pago_id": pago.pk,
        "documento_id": pago.documento_id,
        "proveedor": pago.documento.proveedor,
        "centro_costo": pago.documento.centro_costo,
        "fecha_pago": pago.fecha,
        "monto": pago.monto,
        "medio_pago": pago.medio_pago,
        "referencia": pago.referencia,
        "anulado": False,
        "origen": "COMPRA_PAGO",
        "origen_id": pago.pk,
        "clave_origen": f"COMPRA_PAGO:{pago.pk}",
    } for pago in qs.order_by("fecha", "pk")]


def filas_exportacion_compras(**filtros):
    return _filas_compras(**filtros)


def filas_exportacion_pagos_compras(fecha_desde=None, fecha_hasta=None):
    return [{
        "fecha_pago": fila["fecha_pago"],
        "proveedor": fila["proveedor"].razon_social,
        "documento_id": fila["documento_id"],
        "centro_costo": fila["centro_costo"].codigo if fila["centro_costo"] else "",
        "monto": fila["monto"],
        "medio": fila["medio_pago"],
        "referencia": fila["referencia"],
    } for fila in pagos_para_finanzas(fecha_desde, fecha_hasta)]
