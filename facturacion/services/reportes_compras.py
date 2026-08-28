from decimal import Decimal

from django.db.models import Sum

from facturacion.models import DocumentoCompra, PagoDocumentoCompra
from facturacion.services.iva_compras import documentos_del_periodo, resumen_iva_compras


def saldo_documento(documento, fecha_corte=None):
    pagos = documento.pagos.filter(anulado=False)
    if fecha_corte:
        pagos = pagos.filter(fecha__lte=fecha_corte)
    pagado = pagos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    return documento.total - pagado


def documentos_filtrados(**filtros):
    base = documentos_del_periodo(**{k: v for k, v in filtros.items() if k in {"fecha_desde", "fecha_hasta", "proveedor", "centro_costo", "tipo_documento"}})
    if filtros.get("estado") == DocumentoCompra.Estado.ANULADO:
        base = DocumentoCompra.objects.select_related("proveedor", "centro_costo").filter(estado=filtros["estado"])
        if filtros.get("fecha_desde"): base = base.filter(fecha_documento__gte=filtros["fecha_desde"])
        if filtros.get("fecha_hasta"): base = base.filter(fecha_documento__lte=filtros["fecha_hasta"])
        for campo in ("proveedor", "centro_costo", "tipo_documento"):
            if filtros.get(campo): base = base.filter(**{campo: filtros[campo]})
    elif filtros.get("estado"):
        base = base.filter(estado=filtros["estado"])
    return base


def resumen_compras(fecha_corte=None, **filtros):
    documentos = list(documentos_filtrados(**filtros))
    documental = resumen_iva_compras(**{k: v for k, v in filtros.items() if k in {"fecha_desde", "fecha_hasta", "proveedor", "centro_costo", "tipo_documento"}})
    pagado = sum((documento.total - saldo_documento(documento, fecha_corte) for documento in documentos), Decimal("0.00"))
    pendiente = sum((saldo_documento(documento, fecha_corte) for documento in documentos), Decimal("0.00"))
    return {"cantidad_documentos": len(documentos), "cantidad_proveedores": len({d.proveedor_id for d in documentos}), "neto": documental["neto"], "iva": documental["iva"], "total_documentado": documental["total"], "total_pagado": pagado, "saldo_pendiente": pendiente, "documentos": documentos}


def _agrupado(documentos, campo, fecha_corte=None):
    grupos = {}
    for documento in documentos:
        objeto = getattr(documento, campo)
        clave = objeto.pk if objeto else None
        grupo = grupos.setdefault(clave, {campo: objeto, "cantidad_documentos": 0, "neto": Decimal("0.00"), "iva": Decimal("0.00"), "total": Decimal("0.00"), "pagado": Decimal("0.00"), "pendiente": Decimal("0.00")})
        grupo["cantidad_documentos"] += 1
        grupo["neto"] += documento.neto
        grupo["iva"] += documento.iva
        grupo["total"] += documento.total
        grupo["pendiente"] += saldo_documento(documento, fecha_corte)
        grupo["pagado"] += documento.total - saldo_documento(documento, fecha_corte)
    return list(grupos.values())


def totales_por_proveedor(fecha_corte=None, **filtros):
    return _agrupado(documentos_filtrados(**filtros), "proveedor", fecha_corte)


def totales_por_centro(fecha_corte=None, **filtros):
    return _agrupado(documentos_filtrados(**filtros), "centro_costo", fecha_corte)


def totales_por_estado(fecha_corte=None, **filtros):
    grupos = {}
    for documento in documentos_filtrados(**filtros):
        pagado = documento.total - saldo_documento(documento, fecha_corte)
        estado = DocumentoCompra.Estado.REGISTRADO if pagado == 0 else DocumentoCompra.Estado.PAGADO if pagado >= documento.total else DocumentoCompra.Estado.PARCIAL
        grupo = grupos.setdefault(estado, {"estado": estado, "cantidad_documentos": 0, "total": Decimal("0.00")})
        grupo["cantidad_documentos"] += 1
        grupo["total"] += documento.total
    return list(grupos.values())


def saldos_pendientes(fecha_corte=None, **filtros):
    return [{"documento": d, "proveedor": d.proveedor, "total": d.total, "pagado": d.total - saldo_documento(d, fecha_corte), "saldo": saldo_documento(d, fecha_corte)} for d in documentos_filtrados(**filtros) if saldo_documento(d, fecha_corte) > 0]


def pagos_del_periodo(fecha_desde=None, fecha_hasta=None, proveedor=None):
    qs = PagoDocumentoCompra.objects.select_related("documento__proveedor").filter(anulado=False)
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    if proveedor: qs = qs.filter(documento__proveedor=proveedor)
    return qs.order_by("fecha", "pk")


def filas_exportacion_compras(fecha_corte=None, **filtros):
    return [{"fecha_documento": d.fecha_documento, "fecha_recepcion": d.fecha_recepcion, "rut_proveedor": d.proveedor.rut, "proveedor": d.proveedor.razon_social, "tipo": d.tipo_documento, "numero": d.numero, "centro_costo": d.centro_costo.codigo if d.centro_costo else "", "neto": d.neto, "iva": d.iva, "total": d.total, "pagado": d.total - saldo_documento(d, fecha_corte), "saldo": saldo_documento(d, fecha_corte), "estado": d.estado} for d in documentos_filtrados(**filtros)]
