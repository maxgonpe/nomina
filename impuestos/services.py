from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from impuestos.models import PeriodoImpuesto


def _cambiar(periodo, estado, usuario=None):
    periodo.estado = estado
    if estado == PeriodoImpuesto.Estado.CERRADO:
        periodo.cerrado_en = timezone.now()
        periodo.cerrado_por = usuario
        periodo.save(update_fields=["estado", "cerrado_en", "cerrado_por", "actualizado_en"])
    else:
        periodo.save(update_fields=["estado", "actualizado_en"])
    return periodo


@transaction.atomic
def abrir_periodo(periodo):
    if periodo.estado != PeriodoImpuesto.Estado.BORRADOR:
        raise ValidationError("Solo un período en borrador puede abrirse para cálculo.")
    return periodo


@transaction.atomic
def validar_periodo(periodo):
    if periodo.estado != PeriodoImpuesto.Estado.CALCULADO:
        raise ValidationError("El período debe estar calculado antes de validarse.")
    return _cambiar(periodo, PeriodoImpuesto.Estado.VALIDADO)


@transaction.atomic
def cerrar_periodo(periodo, usuario=None):
    if periodo.estado not in (PeriodoImpuesto.Estado.VALIDADO, PeriodoImpuesto.Estado.DECLARADO):
        raise ValidationError("El período debe estar validado antes de cerrarse.")
    return _cambiar(periodo, PeriodoImpuesto.Estado.CERRADO, usuario)


@transaction.atomic
def reabrir_periodo(periodo, usuario=None):
    if periodo.estado != PeriodoImpuesto.Estado.CERRADO:
        raise ValidationError("Solo un período cerrado puede reabrirse.")
    periodo.cerrado_en = None
    periodo.cerrado_por = None
    periodo.actualizado_por = usuario
    periodo.save(update_fields=["estado", "cerrado_en", "cerrado_por", "actualizado_por", "actualizado_en"])
    return _cambiar(periodo, PeriodoImpuesto.Estado.BORRADOR, usuario)


def periodos_pendientes():
    return PeriodoImpuesto.objects.exclude(estado=PeriodoImpuesto.Estado.CERRADO)
