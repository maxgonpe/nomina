from django.db import transaction

from facturacion.models import PagoDocumentoCompra
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero
from impuestos.models import PagoImpuesto


@transaction.atomic
def movimiento_por_pago_compra(pago):
    if pago.anulado or pago.documento.estado == pago.documento.Estado.ANULADO:
        return None
    categoria = CategoriaFinanciera.objects.get(codigo="EGR_PROVEEDORES", activo=True)
    movimiento, _ = MovimientoFinanciero.objects.update_or_create(origen=MovimientoFinanciero.Origen.COMPRA, pago_compra=pago, defaults={"fecha": pago.fecha, "tipo": MovimientoFinanciero.Tipo.EGRESO, "categoria": categoria, "centro_costo": pago.documento.centro_costo, "documento_compra": pago.documento, "descripcion": f"Pago proveedor {pago.documento.numero}", "monto": pago.monto, "referencia": pago.referencia, "observaciones": pago.observaciones})
    return movimiento


@transaction.atomic
def movimiento_por_pago_impuesto(pago):
    if pago.anulado:
        return None
    categoria = CategoriaFinanciera.objects.get(codigo="EGR_IMPUESTOS", activo=True)
    movimiento, _ = MovimientoFinanciero.objects.update_or_create(origen=MovimientoFinanciero.Origen.IMPUESTO, pago_impuesto=pago, defaults={"fecha": pago.fecha, "tipo": MovimientoFinanciero.Tipo.EGRESO, "categoria": categoria, "periodo_impuesto": pago.periodo, "descripcion": f"Pago impuestos {pago.periodo}", "monto": pago.monto, "referencia": pago.referencia, "observaciones": pago.observaciones})
    return movimiento


def sincronizar_pagos_compras(fecha_desde=None, fecha_hasta=None):
    qs = PagoDocumentoCompra.objects.select_related("documento").filter(anulado=False).exclude(documento__estado="ANULADO")
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    return [movimiento_por_pago_compra(pago) for pago in qs.order_by("fecha", "pk")]


def sincronizar_pagos_impuestos(fecha_desde=None, fecha_hasta=None):
    qs = PagoImpuesto.objects.select_related("periodo").filter(anulado=False)
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    return [movimiento_por_pago_impuesto(pago) for pago in qs.order_by("fecha", "pk")]
