from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from impuestos.models import PeriodoImpuesto


def determinar_periodo(periodo):
    """Consolida resultados oficiales; no vuelve a calcular facturas ni PPM."""
    if periodo.estado not in (PeriodoImpuesto.Estado.CALCULADO, PeriodoImpuesto.Estado.BORRADOR):
        raise ValidationError("El período no está abierto para determinación.")
    if periodo.estado == PeriodoImpuesto.Estado.BORRADOR or not periodo.detalles.exists():
        raise ValidationError("IMP002 debe estar calculado antes de determinar.")
    if periodo.tasa_ppm_snapshot == 0 and periodo.total_ppm == 0:
        raise ValidationError("IMP003 debe estar calculado antes de determinar.")
    iva = periodo.iva_ventas - periodo.iva_compras
    periodo.subtotal_iva = iva
    periodo.monto_a_pagar = iva + periodo.total_ppm
    periodo.save(update_fields=["subtotal_iva", "monto_a_pagar", "actualizado_en"])
    return {"iva_determinado": iva, "ppm": periodo.total_ppm, "total_determinado": periodo.monto_a_pagar}


def validar_determinacion(periodo):
    if periodo.estado != PeriodoImpuesto.Estado.CALCULADO:
        raise ValidationError("El período debe estar calculado para validarse.")
    if periodo.tasa_ppm_snapshot == 0 and periodo.total_ppm == 0:
        raise ValidationError("Falta el resultado de PPM.")
    periodo.estado = PeriodoImpuesto.Estado.VALIDADO
    periodo.save(update_fields=["estado", "actualizado_en"])
    return periodo
