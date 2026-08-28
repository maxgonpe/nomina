import hashlib
import json

from django.core.exceptions import ValidationError
from django.db import transaction

from balance.models import CierreBalance
from balance.services import balance_a_fecha


def _resumen_fuentes(fecha_corte):
    from facturacion.models import DocumentoCompra, DocumentoTributario
    from finanzas.models import MovimientoFinanciero
    return {
        "movimientos_financieros": MovimientoFinanciero.objects.filter(fecha__lte=fecha_corte, anulado=False).count(),
        "documentos_venta": DocumentoTributario.objects.filter(fecha_emision__lte=fecha_corte).exclude(estado="ANULADA").count(),
        "documentos_compra": DocumentoCompra.objects.filter(fecha_documento__lte=fecha_corte).exclude(estado="ANULADO").count(),
    }


@transaction.atomic
def cerrar_balance(fecha_corte, usuario=None):
    calculado = balance_a_fecha(fecha_corte)
    fuentes = _resumen_fuentes(fecha_corte)
    return CierreBalance.objects.update_or_create(fecha_corte=fecha_corte, defaults={"estado": "CERRADO", "caja": calculado["caja"]["saldo"], "cuentas_por_cobrar": calculado["cuentas_por_cobrar"], "obligaciones": calculado["obligaciones_financieras"], "resultado": calculado["resultado_gestion"], "posicion_disponible": calculado["posicion_disponible"], "resumen_fuentes": fuentes, "cerrado_por": usuario})[0]


def reabrir_balance(cierre):
    if cierre.estado != "CERRADO":
        raise ValidationError("El balance no está cerrado.")
    cierre.estado = "REABIERTO"
    cierre.save(update_fields=["estado", "actualizado_en"])
    return cierre


def filas_exportacion_balance(fecha_corte):
    resultado = balance_a_fecha(fecha_corte)
    return [{"fecha_corte": fecha_corte, "linea": linea, "valor": valor} for linea, valor in (("CAJA", resultado["caja"]["saldo"]), ("CUENTAS_POR_COBRAR", resultado["cuentas_por_cobrar"]), ("OBLIGACIONES_FINANCIERAS", resultado["obligaciones_financieras"]), ("RESULTADO_GESTION", resultado["resultado_gestion"]), ("POSICION_DISPONIBLE", resultado["posicion_disponible"]))]


def huella_cierre(cierre):
    contenido = json.dumps(cierre.resumen_fuentes, sort_keys=True).encode()
    return hashlib.sha256(contenido).hexdigest()
