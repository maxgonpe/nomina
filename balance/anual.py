import calendar
from datetime import date
from decimal import Decimal

from balance.services import balance_a_fecha, resultado_gestion


def reporte_anual(anio):
    meses = []
    saldo_anterior = Decimal("0.00")
    for mes in range(1, 13):
        corte = date(anio, mes, calendar.monthrange(anio, mes)[1])
        anterior = date(anio, mes - 1, calendar.monthrange(anio, mes - 1)[1]) if mes > 1 else date(anio - 1, 12, 31)
        actual = balance_a_fecha(corte)
        previo = balance_a_fecha(anterior)
        variacion = actual["caja"]["saldo"] - previo["caja"]["saldo"]
        meses.append({"mes": mes, "caja": actual["caja"]["saldo"], "cobrar": actual["cuentas_por_cobrar"], "obligaciones": actual["obligaciones_financieras"], "resultado": resultado_gestion(date(anio, mes, 1), corte), "variacion_caja": variacion, "tiene_datos": variacion != 0 or actual["resultado_gestion"] != 0})
    return {"anio": anio, "meses": meses, "total_resultado": sum((m["resultado"] for m in meses), Decimal("0.00")), "saldo_final": meses[-1]["caja"]}


def comparar_periodos(anio_a, anio_b):
    primero = reporte_anual(anio_a)
    segundo = reporte_anual(anio_b)
    return {"primero": primero, "segundo": segundo, "diferencia_resultado": segundo["total_resultado"] - primero["total_resultado"], "diferencia_saldo": segundo["saldo_final"] - primero["saldo_final"]}
