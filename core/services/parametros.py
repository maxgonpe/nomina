from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from core.models import ParametroValor

CODIGO_FACTOR_HE = "FACTOR_HE"


def valor(codigo, fecha):
    """
    Valor vigente del parámetro a una fecha.
    Las fórmulas deben usar esto; nunca un literal como 0.0079545.
    """
    if fecha is None:
        raise ValidationError("La fecha es obligatoria para consultar un parámetro.")
    codigo = (codigo or "").strip().upper()
    if not codigo:
        raise ValidationError("El código del parámetro es obligatorio.")

    registro = (
        ParametroValor.objects.filter(
            parametro__codigo=codigo,
            parametro__activo=True,
            vigencia_desde__lte=fecha,
        )
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=fecha))
        .select_related("parametro")
        .order_by("-vigencia_desde")
        .first()
    )
    if registro is None:
        raise ValidationError(
            f"No hay un valor vigente de {codigo} al "
            f"{fecha.strftime('%d-%m-%Y')}."
        )
    return registro.valor


def valor_hora_extra(sueldo_base, fecha):
    factor = valor(CODIGO_FACTOR_HE, fecha)
    return Decimal(sueldo_base) * factor
