from datetime import date
from decimal import Decimal

from django.db.models import Sum

from facturacion.models import DocumentoTributario
from finanzas.flujo import movimientos_vigentes
from finanzas.models import MovimientoFinanciero, ObligacionFinanciera
from finanzas.obligaciones import saldo as saldo_obligacion


ZERO = Decimal("0.00")


def caja_a_fecha(fecha_corte):
    movimientos = movimientos_vigentes(fecha_hasta=fecha_corte)
    ingresos = movimientos.filter(tipo=MovimientoFinanciero.Tipo.INGRESO).aggregate(total=Sum("monto"))["total"] or ZERO
    egresos = movimientos.filter(tipo=MovimientoFinanciero.Tipo.EGRESO).aggregate(total=Sum("monto"))["total"] or ZERO
    return {"ingresos": ingresos, "egresos": egresos, "saldo": ingresos - egresos}


def cuentas_por_cobrar(fecha_corte):
    documentos = DocumentoTributario.objects.filter(fecha_emision__lte=fecha_corte).exclude(estado=DocumentoTributario.Estado.ANULADA).prefetch_related("cobros")
    total = ZERO
    for documento in documentos:
        cobrado = sum((c.monto for c in documento.cobros.all() if not c.anulado and c.fecha <= fecha_corte), ZERO)
        total += documento.total - cobrado
    return total


def obligaciones_financieras(fecha_corte):
    obligaciones = ObligacionFinanciera.objects.exclude(estado=ObligacionFinanciera.Estado.ANULADA)
    return sum((saldo_obligacion(o, fecha_corte) for o in obligaciones), ZERO)


def resultado_gestion(fecha_desde=None, fecha_corte=None):
    movimientos = movimientos_vigentes(fecha_desde, fecha_corte)
    return sum((m.monto if m.tipo == MovimientoFinanciero.Tipo.INGRESO else -m.monto for m in movimientos if m.categoria.afecta_resultado), ZERO)


def balance_a_fecha(fecha_corte, fecha_desde=None):
    if not fecha_corte:
        raise ValueError("fecha_corte es obligatoria")
    caja = caja_a_fecha(fecha_corte)
    cobrar = cuentas_por_cobrar(fecha_corte)
    obligaciones = obligaciones_financieras(fecha_corte)
    resultado = resultado_gestion(fecha_desde, fecha_corte)
    return {
        "fecha_corte": fecha_corte,
        "caja": caja,
        "cuentas_por_cobrar": cobrar,
        "obligaciones_financieras": obligaciones,
        "resultado_gestion": resultado,
        "posicion_disponible": caja["saldo"] + cobrar - obligaciones,
        "estado": "OK",
    }
