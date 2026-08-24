from decimal import Decimal

from django.db.models import Sum

from remuneraciones.models import HoraExtra


def suma_horas_extra(trabajador, periodo):
    """
    Insumo oficial de REM005: SUM(HoraExtra.horas) del trabajador en el período.
    Sustituye los SUMIFS / SUMAR.SI.CONJUNTO del Excel.
    """
    total = HoraExtra.objects.filter(
        trabajador=trabajador,
        periodo=periodo,
    ).aggregate(total=Sum("horas"))["total"]
    return total or Decimal("0.00")


def totales_horas_extra_por_trabajador(periodo):
    return (
        HoraExtra.objects.filter(periodo=periodo)
        .values(
            "trabajador_id",
            "trabajador__nombre_completo",
        )
        .annotate(total=Sum("horas"))
        .order_by("trabajador__nombre_completo")
    )
