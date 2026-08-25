"""
REM010 — Resumen anual de remuneraciones.

Reporte dinámico (no modelo Resumen2026 ni columnas ene–dic).
Fuente: LiquidacionMensual + PeriodoRemuneracion + Trabajador.
"""

from decimal import Decimal

from django.db.models import Prefetch

from remuneraciones.models import (
    NOMBRE_MES,
    HOJA_EXCEL_MES,
    LiquidacionMensual,
    PagoRemuneracion,
    PeriodoRemuneracion,
)
from remuneraciones.services.movimientos import dinero

METRICA_A_PAGAR = "a_pagar"
METRICA_PAGADO = "pagado"

METRICAS = {
    METRICA_A_PAGAR: {
        "label": "Total a pagar",
        "descripcion": (
            "Suma de liquidacion.total_a_pagar "
            "(neto de la liquidación, no necesariamente pagado)."
        ),
    },
    METRICA_PAGADO: {
        "label": "Total pagado",
        "descripcion": (
            "Suma de PagoRemuneracion registrados "
            "(lo efectivamente pagado al trabajador)."
        ),
    },
}

NOMBRE_MES_CORTO = {
    1: "Ene",
    2: "Feb",
    3: "Mar",
    4: "Abr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dic",
}


def meses_del_anio():
    return [
        {
            "numero": mes,
            "nombre": NOMBRE_MES[mes],
            "nombre_corto": NOMBRE_MES_CORTO[mes],
            "etiqueta_grafico": HOJA_EXCEL_MES[mes],
        }
        for mes in range(1, 13)
    ]


def _queryset_liquidaciones(anio, *, trabajador_id=None, centro_costo_id=None):
    qs = (
        LiquidacionMensual.objects.filter(periodo__anio=anio)
        .exclude(estado=LiquidacionMensual.Estado.ANULADA)
        .exclude(estado=LiquidacionMensual.Estado.BORRADOR)
        .select_related(
            "trabajador",
            "periodo",
            "centro_costo",
        )
        .prefetch_related(
            Prefetch(
                "pagos",
                queryset=PagoRemuneracion.objects.only(
                    "id", "liquidacion_id", "monto"
                ),
            )
        )
        .order_by(
            "trabajador__nombre_completo",
            "periodo__mes",
        )
    )
    if trabajador_id:
        qs = qs.filter(trabajador_id=trabajador_id)
    if centro_costo_id:
        qs = qs.filter(centro_costo_id=centro_costo_id)
    return qs


def _monto_liquidacion(liquidacion, metrica):
    if metrica == METRICA_PAGADO:
        return dinero(liquidacion.total_pagado)
    return dinero(liquidacion.total_a_pagar or 0)


def resumen_anual(
    anio,
    *,
    metrica=METRICA_A_PAGAR,
    trabajador_id=None,
    centro_costo_id=None,
):
    """
    Construye la nómina anual, totales por trabajador/mes y dataset del gráfico.
    Meses sin liquidación = 0 (no se arrastra el valor anterior).
    """
    if metrica not in METRICAS:
        metrica = METRICA_A_PAGAR

    meses = meses_del_anio()
    por_trabajador = {}
    totales_mes = {m: Decimal("0.00") for m in range(1, 13)}

    for liq in _queryset_liquidaciones(
        anio,
        trabajador_id=trabajador_id,
        centro_costo_id=centro_costo_id,
    ):
        tid = liq.trabajador_id
        if tid not in por_trabajador:
            por_trabajador[tid] = {
                "trabajador_id": tid,
                "nombre": liq.trabajador.nombre_completo,
                "rut": liq.trabajador.rut_formateado,
                "cargo": liq.cargo_nombre_snapshot or "",
                "meses": {m: Decimal("0.00") for m in range(1, 13)},
                "total": Decimal("0.00"),
            }
        fila = por_trabajador[tid]
        if liq.cargo_nombre_snapshot:
            fila["cargo"] = liq.cargo_nombre_snapshot
        mes = liq.periodo.mes
        monto = _monto_liquidacion(liq, metrica)
        # Una liquidación oficial por período+trabajador: se reemplaza, no suma
        anterior = fila["meses"][mes]
        fila["meses"][mes] = monto
        fila["total"] = dinero(fila["total"] - anterior + monto)
        totales_mes[mes] = dinero(totales_mes[mes] - anterior + monto)

    filas = sorted(por_trabajador.values(), key=lambda f: f["nombre"].lower())
    for fila in filas:
        fila["valores_mes"] = [fila["meses"][m] for m in range(1, 13)]
    total_anual = dinero(sum((f["total"] for f in filas), Decimal("0.00")))

    grafico = {
        "labels": [m["etiqueta_grafico"] for m in meses],
        "valores": [float(totales_mes[m["numero"]]) for m in meses],
    }

    return {
        "anio": anio,
        "metrica": metrica,
        "metrica_label": METRICAS[metrica]["label"],
        "metrica_descripcion": METRICAS[metrica]["descripcion"],
        "meses": meses,
        "filas": filas,
        "totales_mes": [totales_mes[m["numero"]] for m in meses],
        "totales_mes_dict": totales_mes,
        "total_anual": total_anual,
        "grafico": grafico,
        "anios_disponibles": anios_con_datos(),
    }


def anios_con_datos():
    anios = list(
        PeriodoRemuneracion.objects.order_by("-anio")
        .values_list("anio", flat=True)
        .distinct()
    )
    return anios


def filas_exportacion(resumen):
    """
    Filas listas para Excel (integracion_excel):
    NOMBRE | RUT | CARGO | ENE…DIC | TOTAL
    """
    encabezado = (
        ["NOMBRE", "RUT", "CARGO"]
        + [m["etiqueta_grafico"] for m in resumen["meses"]]
        + ["TOTAL"]
    )
    filas = [encabezado]
    for fila in resumen["filas"]:
        filas.append(
            [
                fila["nombre"],
                fila["rut"],
                fila["cargo"],
            ]
            + [fila["meses"][m["numero"]] for m in resumen["meses"]]
            + [fila["total"]]
        )
    filas.append(
        ["TOTAL", "", ""]
        + list(resumen["totales_mes"])
        + [resumen["total_anual"]]
    )
    return filas
