from django.core.exceptions import ValidationError
from django.db import transaction

from finanzas.models import CategoriaFinanciera, MovimientoFinanciero
from remuneraciones.models import PagoRemuneracion


@transaction.atomic
def movimiento_por_pago_remuneracion(pago):
    if pago.anulado:
        return None
    categoria = CategoriaFinanciera.objects.get(codigo="EGR_REMUNERACIONES", activo=True)
    centro = pago.liquidacion.centro_costo
    movimiento, _ = MovimientoFinanciero.objects.update_or_create(
        origen=MovimientoFinanciero.Origen.REMUNERACION,
        pago_remuneracion=pago,
        defaults={"fecha": pago.fecha, "tipo": MovimientoFinanciero.Tipo.EGRESO, "categoria": categoria, "centro_costo": centro, "trabajador": pago.liquidacion.trabajador, "liquidacion": pago.liquidacion, "descripcion": f"Pago remuneración {pago.liquidacion.trabajador}", "monto": pago.monto, "referencia": pago.referencia, "observaciones": pago.observaciones},
    )
    return movimiento


def pagos_remuneracion_para_finanzas(fecha_desde=None, fecha_hasta=None):
    qs = PagoRemuneracion.objects.select_related("liquidacion__trabajador", "liquidacion__centro_costo").filter(anulado=False)
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    return qs.order_by("fecha", "pk")


def sincronizar_pagos_remuneracion(fecha_desde=None, fecha_hasta=None):
    return [movimiento_por_pago_remuneracion(pago) for pago in pagos_remuneracion_para_finanzas(fecha_desde, fecha_hasta)]
