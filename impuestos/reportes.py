from decimal import Decimal

from impuestos.models import PeriodoImpuesto, PagoImpuesto
from impuestos.pagos import situacion_pago


def resumen_periodo(periodo):
    compras = periodo.detalles.filter(tipo="IVA_COMPRA")
    neto_compras = sum((d.neto for d in compras), Decimal("0.00"))
    return {
        "periodo": periodo, "estado": periodo.estado,
        "neto_ventas": periodo.neto_ventas, "iva_ventas": periodo.iva_ventas,
        "neto_compras": neto_compras, "iva_compras": periodo.iva_compras,
        "iva_determinado": periodo.subtotal_iva,
        "remanente": max(-periodo.subtotal_iva, Decimal("0.00")),
        "base_ppm": periodo.neto_ventas, "tasa_ppm": periodo.tasa_ppm_snapshot,
        "ppm": periodo.total_ppm, "total_determinado": periodo.monto_a_pagar,
        "total_pagado": periodo.total_pagado, "saldo": periodo.saldo_pendiente,
        "situacion_pago": situacion_pago(periodo),
    }


def periodos_filtrados(anio=None, mes=None, estado=None):
    qs = PeriodoImpuesto.objects.all()
    if anio: qs = qs.filter(anio=anio)
    if mes: qs = qs.filter(mes=mes)
    if estado: qs = qs.filter(estado=estado)
    return qs.order_by("anio", "mes")


def resumen_anual(anio):
    periodos = list(periodos_filtrados(anio=anio))
    res = [resumen_periodo(p) for p in periodos]
    suma = lambda campo: sum((r[campo] for r in res), Decimal("0.00"))
    return {"anio": anio, "periodos": res, "iva_ventas": suma("iva_ventas"), "iva_compras": suma("iva_compras"), "ppm": suma("ppm"), "total_determinado": suma("total_determinado"), "total_pagado": suma("total_pagado"), "saldo": suma("saldo"), "periodos_pendientes": [r for r in res if r["saldo"] > 0], "periodos_no_cerrados": [r for r in res if r["estado"] != PeriodoImpuesto.Estado.CERRADO]}


def pagos_por_periodo(anio=None, mes=None):
    qs = PagoImpuesto.objects.select_related("periodo").filter(anulado=False)
    if anio: qs = qs.filter(periodo__anio=anio)
    if mes: qs = qs.filter(periodo__mes=mes)
    return qs.order_by("fecha", "pk")


def pagos_por_fecha(fecha_desde=None, fecha_hasta=None):
    qs = PagoImpuesto.objects.select_related("periodo").filter(anulado=False)
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    return qs.order_by("fecha", "pk")


def saldos_tributarios(anio=None):
    return [r for r in resumen_anual(anio)["periodos"] if r["saldo"] > 0]


def filas_exportacion_impuestos(anio=None):
    return [{k: resumen[k] for k in ("periodo", "estado", "neto_ventas", "iva_ventas", "neto_compras", "iva_compras", "iva_determinado", "remanente", "base_ppm", "tasa_ppm", "ppm", "total_determinado", "total_pagado", "saldo", "situacion_pago")} for resumen in resumen_anual(anio)["periodos"]]
