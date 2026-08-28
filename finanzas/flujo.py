import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from finanzas.models import CategoriaFinanciera, CierreFinancieroMensual, MovimientoFinanciero


def movimientos_vigentes(fecha_desde=None, fecha_hasta=None):
    qs = MovimientoFinanciero.objects.select_related("categoria", "centro_costo").filter(anulado=False)
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    return qs.order_by("fecha", "pk")


def _totales(qs):
    ingresos = qs.filter(tipo=MovimientoFinanciero.Tipo.INGRESO).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    egresos = qs.filter(tipo=MovimientoFinanciero.Tipo.EGRESO).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    return {"ingresos": ingresos, "egresos": egresos, "resultado": ingresos - egresos}


def flujo_mensual(anio, mes):
    inicio = date(anio, mes, 1)
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1])
    periodo = _totales(movimientos_vigentes(inicio, fin))
    anterior = _totales(movimientos_vigentes(fecha_hasta=inicio.replace(day=1) - timedelta(days=1)))
    periodo["saldo_inicial"] = anterior["resultado"]
    periodo["saldo_final"] = periodo["saldo_inicial"] + periodo["resultado"]
    periodo["movimientos"] = movimientos_vigentes(inicio, fin)
    return periodo


def totales_por_categoria(anio, mes):
    grupos = {}
    for movimiento in flujo_mensual(anio, mes)["movimientos"]:
        grupo = grupos.setdefault(movimiento.categoria_id, {"categoria": movimiento.categoria, "ingresos": Decimal("0.00"), "egresos": Decimal("0.00")})
        grupo["ingresos" if movimiento.tipo == "INGRESO" else "egresos"] += movimiento.monto
    return list(grupos.values())


def totales_por_grupo(anio, mes):
    grupos = {}
    for movimiento in flujo_mensual(anio, mes)["movimientos"]:
        clave = movimiento.categoria.grupo_flujo
        grupo = grupos.setdefault(clave, {"grupo_flujo": clave, "ingresos": Decimal("0.00"), "egresos": Decimal("0.00"), "resultado": Decimal("0.00")})
        grupo["ingresos" if movimiento.tipo == MovimientoFinanciero.Tipo.INGRESO else "egresos"] += movimiento.monto
        if movimiento.categoria.afecta_resultado:
            grupo["resultado"] += movimiento.monto if movimiento.tipo == MovimientoFinanciero.Tipo.INGRESO else -movimiento.monto
    return list(grupos.values())


def resultado_operacional(anio, mes):
    movimientos = flujo_mensual(anio, mes)["movimientos"]
    return sum((m.monto if m.tipo == MovimientoFinanciero.Tipo.INGRESO else -m.monto for m in movimientos if m.categoria.grupo_flujo == CategoriaFinanciera.GrupoFlujo.OPERACION and m.categoria.afecta_resultado), Decimal("0.00"))


def totales_por_centro(anio, mes):
    grupos = {}
    for movimiento in flujo_mensual(anio, mes)["movimientos"]:
        key = movimiento.centro_costo_id
        grupo = grupos.setdefault(key, {"centro_costo": movimiento.centro_costo, "ingresos": Decimal("0.00"), "egresos": Decimal("0.00")})
        grupo["ingresos" if movimiento.tipo == "INGRESO" else "egresos"] += movimiento.monto
    return list(grupos.values())


def calcular_cierre(cierre):
    flujo = flujo_mensual(cierre.anio, cierre.mes)
    cierre.saldo_inicial = flujo["saldo_inicial"]
    cierre.ingresos = flujo["ingresos"]
    cierre.egresos = flujo["egresos"]
    cierre.saldo_final = flujo["saldo_final"]
    cierre.estado = CierreFinancieroMensual.Estado.CALCULADO
    cierre.save(update_fields=["saldo_inicial", "ingresos", "egresos", "saldo_final", "estado", "actualizado_en"])
    return cierre
