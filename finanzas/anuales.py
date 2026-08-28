import calendar
from datetime import date
from decimal import Decimal

from finanzas.flujo import movimientos_vigentes
from finanzas.models import MovimientoFinanciero


def reporte_anual(anio, mes_desde=1, mes_hasta=12, categoria=None, centro_costo=None, tipo=None, origen=None):
    filtros = {"fecha_desde": date(anio, mes_desde, 1), "fecha_hasta": date(anio, mes_hasta, calendar.monthrange(anio, mes_hasta)[1])}
    qs = movimientos_vigentes(**filtros)
    if categoria: qs = qs.filter(categoria=categoria)
    if centro_costo: qs = qs.filter(centro_costo=centro_costo)
    if tipo: qs = qs.filter(tipo=tipo)
    if origen: qs = qs.filter(origen=origen)
    movimientos = list(qs)
    meses = []
    saldo = Decimal("0.00")
    for mes in range(mes_desde, mes_hasta + 1):
        del_mes = [m for m in movimientos if m.fecha.month == mes]
        ingresos = sum((m.monto for m in del_mes if m.tipo == "INGRESO"), Decimal("0.00"))
        egresos = sum((m.monto for m in del_mes if m.tipo == "EGRESO"), Decimal("0.00"))
        inicial = saldo
        saldo += ingresos - egresos
        meses.append({"mes": mes, "ingresos": ingresos, "egresos": egresos, "resultado": ingresos - egresos, "saldo_inicial": inicial, "saldo_final": saldo, "tiene_datos": bool(del_mes), "movimientos": del_mes})
    ingresos = sum((m["ingresos"] for m in meses), Decimal("0.00"))
    egresos = sum((m["egresos"] for m in meses), Decimal("0.00"))
    return {"anio": anio, "meses": meses, "ingresos": ingresos, "egresos": egresos, "resultado": ingresos - egresos, "saldo_final": saldo, "movimientos": movimientos}


def matriz_por_categoria(anio, **filtros):
    reporte = reporte_anual(anio, **filtros)
    matriz = {}
    for movimiento in reporte["movimientos"]:
        fila = matriz.setdefault(movimiento.categoria_id, {"categoria": movimiento.categoria, "meses": {}, "total": Decimal("0.00")})
        valor = movimiento.monto if movimiento.tipo == "INGRESO" else -movimiento.monto
        fila["meses"][movimiento.fecha.month] = fila["meses"].get(movimiento.fecha.month, Decimal("0.00")) + valor
        fila["total"] += valor
    return list(matriz.values())


def totales_por_origen(anio, **filtros):
    grupos = {}
    for movimiento in reporte_anual(anio, **filtros)["movimientos"]:
        fila = grupos.setdefault(movimiento.origen, {"origen": movimiento.origen, "ingresos": Decimal("0.00"), "egresos": Decimal("0.00")})
        fila["ingresos" if movimiento.tipo == "INGRESO" else "egresos"] += movimiento.monto
    return list(grupos.values())


def totales_por_grupo_flujo(anio, **filtros):
    grupos = {}
    for movimiento in reporte_anual(anio, **filtros)["movimientos"]:
        clave = movimiento.categoria.grupo_flujo
        fila = grupos.setdefault(clave, {"grupo_flujo": clave, "ingresos": Decimal("0.00"), "egresos": Decimal("0.00"), "resultado": Decimal("0.00")})
        fila["ingresos" if movimiento.tipo == MovimientoFinanciero.Tipo.INGRESO else "egresos"] += movimiento.monto
        if movimiento.categoria.afecta_resultado:
            fila["resultado"] += movimiento.monto if movimiento.tipo == MovimientoFinanciero.Tipo.INGRESO else -movimiento.monto
    return list(grupos.values())


def filas_exportacion_finanzas(anio, **filtros):
    return [{"anio": anio, "mes": fila["mes"], "ingresos": fila["ingresos"], "egresos": fila["egresos"], "resultado": fila["resultado"], "saldo_inicial": fila["saldo_inicial"], "saldo_final": fila["saldo_final"], "tiene_datos": fila["tiene_datos"]} for fila in reporte_anual(anio, **filtros)["meses"]]


def filas_para_balance(anio, **filtros):
    reporte = reporte_anual(anio, **filtros)
    return {"anio": anio, "ingresos": reporte["ingresos"], "egresos": reporte["egresos"], "resultado": reporte["resultado"], "saldo_final": reporte["saldo_final"]}
