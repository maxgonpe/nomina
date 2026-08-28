from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from facturacion.models import DocumentoCompra, DocumentoTributario
from impuestos.models import DetalleImpuesto, PeriodoImpuesto


def fecha_tributaria_compra(documento):
    """Regla única vigente: la fecha documental determina el período."""
    return documento.fecha_documento


def _signo(tipo):
    tipo = (tipo or "").upper().replace("Í", "I")
    return Decimal("-1") if "NOTA" in tipo and "CRED" in tipo else Decimal("1")


def documentos_ventas(periodo):
    return DocumentoTributario.objects.select_related("cliente", "obra").filter(
        fecha_emision__range=(periodo.fecha_inicio, periodo.fecha_fin)
    ).exclude(estado=DocumentoTributario.Estado.ANULADA).order_by("fecha_emision", "pk")


def documentos_compras(periodo):
    return DocumentoCompra.objects.select_related("proveedor", "centro_costo").filter(
        fecha_documento__range=(periodo.fecha_inicio, periodo.fecha_fin)
    ).exclude(estado=DocumentoCompra.Estado.ANULADO).order_by("fecha_documento", "pk")


def inconsistencias_iva(periodo):
    problemas = []
    documentos = list(documentos_ventas(periodo)) + list(documentos_compras(periodo))
    for documento in documentos:
        if "EXENTA" in (documento.tipo_documento or "").upper():
            if documento.iva != 0:
                problemas.append({"documento": documento, "motivo": "Documento exento con IVA distinto de cero."})
        elif documento.neto + documento.iva != documento.total:
            problemas.append({"documento": documento, "motivo": "Neto más IVA no coincide con total."})
    return problemas


@transaction.atomic
def calcular_iva_periodo(periodo):
    if periodo.estado not in (PeriodoImpuesto.Estado.BORRADOR, PeriodoImpuesto.Estado.CALCULADO):
        raise ValidationError("Solo se puede calcular un período abierto.")
    ventas = list(documentos_ventas(periodo))
    compras = list(documentos_compras(periodo))
    iva_ventas = sum((d.iva * _signo(d.tipo_documento) for d in ventas), Decimal("0.00"))
    iva_compras = sum((d.iva * _signo(d.tipo_documento) for d in compras), Decimal("0.00"))
    neto_ventas = sum((d.neto * _signo(d.tipo_documento) for d in ventas), Decimal("0.00"))
    periodo.iva_ventas = iva_ventas
    periodo.iva_compras = iva_compras
    periodo.subtotal_iva = iva_ventas - iva_compras
    periodo.neto_ventas = neto_ventas
    periodo.estado = PeriodoImpuesto.Estado.CALCULADO
    from django.utils import timezone
    periodo.calculado_en = timezone.now()
    periodo.save(update_fields=["iva_ventas", "iva_compras", "subtotal_iva", "neto_ventas", "estado", "calculado_en", "actualizado_en"])
    periodo.detalles.all().delete()
    DetalleImpuesto.objects.bulk_create([
        DetalleImpuesto(periodo=periodo, tipo=DetalleImpuesto.Tipo.IVA_VENTA, documento_venta=d, neto=d.neto * _signo(d.tipo_documento), iva=d.iva * _signo(d.tipo_documento)) for d in ventas
    ] + [
        DetalleImpuesto(periodo=periodo, tipo=DetalleImpuesto.Tipo.IVA_COMPRA, documento_compra=d, neto=d.neto * _signo(d.tipo_documento), iva=d.iva * _signo(d.tipo_documento)) for d in compras
    ])
    return periodo
