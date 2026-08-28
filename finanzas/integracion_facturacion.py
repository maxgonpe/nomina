from django.db import transaction

from facturacion.models import CobroDocumentoTributario
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero


@transaction.atomic
def movimiento_por_cobro(cobro):
    if cobro.anulado or cobro.documento.estado == cobro.documento.Estado.ANULADA:
        return None
    categoria = CategoriaFinanciera.objects.get(codigo="ING_CLIENTES", activo=True)
    centro = cobro.documento.obra.centro_costo if cobro.documento.obra else None
    movimiento, _ = MovimientoFinanciero.objects.update_or_create(
        origen=MovimientoFinanciero.Origen.FACTURACION,
        cobro_documento=cobro,
        defaults={"fecha": cobro.fecha, "tipo": MovimientoFinanciero.Tipo.INGRESO, "categoria": categoria, "centro_costo": centro, "documento_tributario": cobro.documento, "descripcion": f"Cobro documento {cobro.documento.numero}", "monto": cobro.monto, "referencia": cobro.referencia, "observaciones": cobro.observaciones},
    )
    return movimiento


def cobros_para_finanzas(fecha_desde=None, fecha_hasta=None):
    qs = CobroDocumentoTributario.objects.select_related("documento__obra__centro_costo").filter(anulado=False).exclude(documento__estado="ANULADA")
    if fecha_desde: qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta: qs = qs.filter(fecha__lte=fecha_hasta)
    return qs.order_by("fecha", "pk")


def sincronizar_cobros(fecha_desde=None, fecha_hasta=None):
    return [movimiento_por_cobro(cobro) for cobro in cobros_para_finanzas(fecha_desde, fecha_hasta)]
