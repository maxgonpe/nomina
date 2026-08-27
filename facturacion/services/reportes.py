from calendar import monthrange
from datetime import date
from decimal import Decimal
from django.db.models import Q, Sum
from facturacion.models import DocumentoTributario


def filtrar_documentos(filtros=None):
    qs = DocumentoTributario.objects.select_related("cliente", "obra", "obra__centro_costo").prefetch_related("cobros").all()
    filtros = filtros or {}
    if filtros.get("anio"):
        qs = qs.filter(fecha_emision__year=filtros["anio"])
    if filtros.get("mes"):
        qs = qs.filter(fecha_emision__month=filtros["mes"])
    if filtros.get("desde"):
        qs = qs.filter(fecha_emision__gte=filtros["desde"])
    if filtros.get("hasta"):
        qs = qs.filter(fecha_emision__lte=filtros["hasta"])
    for campo in ("cliente", "obra", "tipo", "estado"):
        if filtros.get(campo):
            qs = qs.filter(**({"tipo_documento" if campo == "tipo" else campo: filtros[campo]}))
    if filtros.get("centro_costo"):
        qs = qs.filter(obra__centro_costo=filtros["centro_costo"])
    return qs.order_by("fecha_emision", "pk")


def resumen_facturacion(filtros=None):
    documentos = list(filtrar_documentos(filtros))
    oficiales = [d for d in documentos if d.estado != DocumentoTributario.Estado.ANULADA]
    return {"documentos": documentos, "neto": sum((d.neto for d in oficiales), Decimal("0.00")), "iva": sum((d.iva for d in oficiales), Decimal("0.00")), "total": sum((d.total for d in oficiales), Decimal("0.00")), "cobrado": sum((d.total_cobrado for d in oficiales), Decimal("0.00")), "saldo": sum((d.saldo_pendiente for d in oficiales), Decimal("0.00")), "anulados": len(documentos) - len(oficiales)}


def totales_mensuales(anio):
    return [resumen_facturacion({"anio": anio, "mes": mes}) for mes in range(1, 13)]
