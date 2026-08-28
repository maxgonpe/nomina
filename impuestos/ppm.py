from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.services.parametros import valor
from impuestos.iva import calcular_iva_periodo
from impuestos.models import PeriodoImpuesto


def base_ppm(periodo):
    """La base única de PPM es el neto de ventas determinado por IMP002."""
    if periodo.estado == PeriodoImpuesto.Estado.BORRADOR:
        calcular_iva_periodo(periodo)
        periodo.refresh_from_db()
    return periodo.neto_ventas


@transaction.atomic
def calcular_ppm(periodo):
    if periodo.estado not in (PeriodoImpuesto.Estado.BORRADOR, PeriodoImpuesto.Estado.CALCULADO):
        raise ValidationError("Solo se puede calcular PPM en un período abierto.")
    base = base_ppm(periodo)
    tasa = valor("TASA_PPM", periodo.fecha_fin)
    monto = (base * Decimal(tasa)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    periodo.tasa_ppm_snapshot = tasa
    periodo.total_ppm = monto
    periodo.calculado_en = timezone.now()
    periodo.save(update_fields=["tasa_ppm_snapshot", "total_ppm", "calculado_en", "actualizado_en"])
    return {"base_ppm": base, "tasa_ppm": tasa, "total_ppm": monto}
