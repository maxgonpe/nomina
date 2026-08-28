from decimal import Decimal

from facturacion.models import DocumentoCompra


def _signo(documento):
    tipo = (documento.tipo_documento or "").upper().replace("Í", "I")
    return Decimal("-1") if "NOTA" in tipo and "CRED" in tipo else Decimal("1")


def documentos_del_periodo(
    fecha_desde=None,
    fecha_hasta=None,
    proveedor=None,
    centro_costo=None,
    tipo_documento=None,
):
    """Retorna documentos no anulados usando fecha_documento como fecha fiscal."""
    qs = DocumentoCompra.objects.select_related("proveedor", "centro_costo").exclude(
        estado=DocumentoCompra.Estado.ANULADO
    )
    if fecha_desde:
        qs = qs.filter(fecha_documento__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_documento__lte=fecha_hasta)
    if proveedor:
        qs = qs.filter(proveedor=proveedor)
    if centro_costo:
        qs = qs.filter(centro_costo=centro_costo)
    if tipo_documento:
        qs = qs.filter(tipo_documento=tipo_documento)
    return qs.order_by("fecha_documento", "pk")


def _importe(documento, campo):
    return getattr(documento, campo) * _signo(documento)


def _fila(documento):
    return {
        "id": documento.pk,
        "proveedor": documento.proveedor,
        "tipo": documento.tipo_documento,
        "numero": documento.numero,
        "fecha_documento": documento.fecha_documento,
        "fecha_recepcion": documento.fecha_recepcion,
        "neto": _importe(documento, "neto"),
        "iva": _importe(documento, "iva"),
        "total": _importe(documento, "total"),
        "tasa_iva_snapshot": documento.tasa_iva_snapshot,
        "estado": documento.estado,
        "centro_costo": documento.centro_costo,
    }


def resumen_iva_compras(**filtros):
    documentos = documentos_del_periodo(**filtros)
    filas = [_fila(documento) for documento in documentos]
    return {
        "cantidad_documentos": len(filas),
        "neto": sum((fila["neto"] for fila in filas), Decimal("0.00")),
        "iva": sum((fila["iva"] for fila in filas), Decimal("0.00")),
        "total": sum((fila["total"] for fila in filas), Decimal("0.00")),
        "documentos": filas,
        "fecha": "fecha_documento",
    }


def _agrupar(documentos, clave):
    agrupado = {}
    for documento in documentos:
        valor = getattr(documento, clave)
        key = valor.pk if valor else None
        grupo = agrupado.setdefault(key, {clave: valor, "cantidad_documentos": 0, "neto": Decimal("0.00"), "iva": Decimal("0.00"), "total": Decimal("0.00")})
        grupo["cantidad_documentos"] += 1
        grupo["neto"] += _importe(documento, "neto")
        grupo["iva"] += _importe(documento, "iva")
        grupo["total"] += _importe(documento, "total")
    return list(agrupado.values())


def totales_por_proveedor(**filtros):
    return _agrupar(documentos_del_periodo(**filtros), "proveedor")


def totales_por_centro(**filtros):
    return _agrupar(documentos_del_periodo(**filtros), "centro_costo")


def validar_consistencia_documentos(**filtros):
    inconsistencias = []
    for documento in documentos_del_periodo(**filtros):
        signo = _signo(documento)
        esperado = (documento.neto + documento.iva) * signo
        total = documento.total * signo
        if "EXENTA" in (documento.tipo_documento or "").upper() and documento.iva != 0:
            inconsistencias.append({"documento": documento, "motivo": "Un documento exento tiene IVA."})
        elif esperado != total:
            inconsistencias.append({"documento": documento, "motivo": "Neto más IVA no coincide con total."})
    return inconsistencias
