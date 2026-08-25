"""
REN006 — Consultas y reportes de rendiciones.

Totales desde Rendicion / RendicionDetalle (sin modelo por mes).
"""

from calendar import month_name
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from rendiciones.models import Rendicion, RendicionDetalle

# Reportes financieros oficiales (REN005 / REN006).
ESTADOS_OFICIALES = (
    Rendicion.Estado.APROBADA,
    Rendicion.Estado.PAGADA,
)

MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def dinero(valor):
    if valor is None:
        return Decimal("0.00")
    return Decimal(valor).quantize(Decimal("0.01"))


def etiquetas_estados(estados):
    labels = dict(Rendicion.Estado.choices)
    return [labels.get(e, e) for e in estados]


def normalizar_estados(estados):
    """Lista de códigos de estado; vacío → todos."""
    if not estados:
        return []
    if isinstance(estados, str):
        estados = [p.strip() for p in estados.split(",") if p.strip()]
    validos = {c for c, _ in Rendicion.Estado.choices}
    return [e for e in estados if e in validos]


def filtrar_rendiciones(
    qs=None,
    *,
    anio=None,
    mes=None,
    fecha=None,
    trabajador_id=None,
    centro_costo_id=None,
    estados=None,
):
    """
    Aplica filtros GET a un queryset de Rendicion.
    centro_costo filtra por existencia de detalle en ese CC.
    """
    if qs is None:
        qs = Rendicion.objects.all()

    estados = normalizar_estados(estados)
    if estados:
        qs = qs.filter(estado__in=estados)
    if anio:
        qs = qs.filter(fecha__year=int(anio))
    if mes:
        qs = qs.filter(fecha__month=int(mes))
    if fecha:
        qs = qs.filter(fecha=fecha)
    if trabajador_id:
        qs = qs.filter(trabajador_id=int(trabajador_id))
    if centro_costo_id:
        qs = qs.filter(
            detalles__centro_costo_id=int(centro_costo_id)
        ).distinct()
    return qs.select_related("trabajador").order_by("-fecha", "-pk")


def resumen_por_centro(
    *,
    anio=None,
    mes=None,
    trabajador_id=None,
    centro_costo_id=None,
    estados=None,
):
    """
    Totales por centro de costo a partir de RendicionDetalle.
    Por defecto solo estados oficiales (APROBADA + PAGADA).
    """
    if estados is None:
        estados = list(ESTADOS_OFICIALES)
    else:
        estados = normalizar_estados(estados) or list(ESTADOS_OFICIALES)

    rendiciones = filtrar_rendiciones(
        anio=anio,
        mes=mes,
        trabajador_id=trabajador_id,
        centro_costo_id=None,
        estados=estados,
    )
    rendicion_ids = list(rendiciones.values_list("pk", flat=True))

    detalles = RendicionDetalle.objects.filter(
        rendicion_id__in=rendicion_ids
    ).select_related("centro_costo")
    if centro_costo_id:
        detalles = detalles.filter(centro_costo_id=int(centro_costo_id))

    agrupado = (
        detalles.values(
            "centro_costo_id",
            "centro_costo__codigo",
            "centro_costo__nombre",
        )
        .annotate(total=Coalesce(Sum("monto"), Decimal("0.00")))
        .order_by("centro_costo__codigo")
    )

    por_centro = [
        {
            "centro_costo_id": fila["centro_costo_id"],
            "codigo": fila["centro_costo__codigo"],
            "nombre": fila["centro_costo__nombre"],
            "total": dinero(fila["total"]),
        }
        for fila in agrupado
    ]
    total = dinero(sum((f["total"] for f in por_centro), Decimal("0.00")))

    por_trabajador_qs = (
        rendiciones.values(
            "trabajador_id",
            "trabajador__nombre_completo",
        )
        .annotate(
            total=Coalesce(Sum("total_declarado"), Decimal("0.00")),
            cantidad=Count("id"),
        )
        .order_by("trabajador__nombre_completo")
    )
    por_trabajador = [
        {
            "trabajador_id": fila["trabajador_id"],
            "nombre": fila["trabajador__nombre_completo"],
            "total": dinero(fila["total"]),
            "cantidad": fila["cantidad"],
        }
        for fila in por_trabajador_qs
    ]
    if trabajador_id:
        por_trabajador = [
            f
            for f in por_trabajador
            if f["trabajador_id"] == int(trabajador_id)
        ]

    total_declarado = dinero(
        sum((f["total"] for f in por_trabajador), Decimal("0.00"))
    )

    titulo_mes = ""
    if mes:
        titulo_mes = MESES_ES.get(int(mes), month_name[int(mes)]).upper()
    titulo = " ".join(
        p for p in (titulo_mes, str(anio) if anio else "") if p
    ).strip() or "Todas las fechas"

    return {
        "titulo": titulo,
        "anio": int(anio) if anio else None,
        "mes": int(mes) if mes else None,
        "estados": list(estados),
        "estados_label": etiquetas_estados(estados),
        "por_centro": por_centro,
        "por_trabajador": por_trabajador,
        "total_distribuido": total,
        "total_declarado": total_declarado,
        "cantidad_rendiciones": len(rendicion_ids),
    }


def filas_exportacion(resumen):
    """
    Filas listas para Excel (integracion_excel):
    CENTRO | NOMBRE | TOTAL  (+ fila TOTAL)
    """
    encabezado = ["CENTRO", "NOMBRE", "TOTAL"]
    filas = [encabezado]
    for fila in resumen["por_centro"]:
        filas.append([fila["codigo"], fila["nombre"], fila["total"]])
    filas.append(["TOTAL", "", resumen["total_distribuido"]])
    return filas


def anios_disponibles():
    years = (
        Rendicion.objects.order_by()
        .values_list("fecha__year", flat=True)
        .distinct()
    )
    return sorted({y for y in years if y}, reverse=True)
