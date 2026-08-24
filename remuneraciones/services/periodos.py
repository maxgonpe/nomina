from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from remuneraciones.models import LiquidacionMensual, PeriodoRemuneracion

Estado = PeriodoRemuneracion.Estado

TRANSICIONES_PERMITIDAS = {
    Estado.BORRADOR: {Estado.ABIERTO},
    Estado.ABIERTO: {Estado.CALCULADO},
    Estado.CALCULADO: {Estado.VALIDADO},
    Estado.VALIDADO: {Estado.CERRADO},
    Estado.CERRADO: set(),
}


def acciones_disponibles(periodo):
    return {
        "abrir": periodo.estado == Estado.BORRADOR,
        "marcar_calculado": periodo.estado == Estado.ABIERTO,
        "validar": periodo.estado == Estado.CALCULADO,
        "cerrar": periodo.estado == Estado.VALIDADO,
        "reabrir": periodo.estado == Estado.CERRADO,
        "editar": periodo.estado != Estado.CERRADO,
    }


def crear(*, anio, mes, usuario=None, observaciones=""):
    periodo = PeriodoRemuneracion(
        anio=anio,
        mes=mes,
        estado=Estado.BORRADOR,
        observaciones=observaciones or "",
        creado_por=usuario,
        actualizado_por=usuario,
    )
    periodo.full_clean()
    periodo.save()
    return periodo


def abrir(periodo, usuario=None):
    return _transicionar(periodo, Estado.ABIERTO, usuario)


def marcar_calculado(periodo, usuario=None):
    return _transicionar(periodo, Estado.CALCULADO, usuario)


def validar(periodo, usuario=None):
    return _transicionar(periodo, Estado.VALIDADO, usuario)


def cerrar(periodo, usuario=None):
    with transaction.atomic():
        periodo = PeriodoRemuneracion.objects.select_for_update().get(
            pk=periodo.pk
        )
        if periodo.estado != Estado.VALIDADO:
            raise ValidationError(
                "Solo se puede cerrar un período validado."
            )
        _validar_liquidaciones_para_cierre(periodo)
        periodo.estado = Estado.CERRADO
        periodo.cerrado_en = timezone.now()
        periodo.cerrado_por = usuario
        if usuario is not None:
            periodo.actualizado_por = usuario
        periodo.save()
    return periodo


def reabrir(periodo, motivo, usuario=None):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError(
            "La reapertura autorizada requiere un motivo."
        )
    with transaction.atomic():
        periodo = PeriodoRemuneracion.objects.select_for_update().get(
            pk=periodo.pk
        )
        if periodo.estado != Estado.CERRADO:
            raise ValidationError(
                "Solo se puede reabrir un período cerrado."
            )
        periodo.estado = Estado.ABIERTO
        periodo.motivo_reapertura = motivo
        if usuario is not None:
            periodo.actualizado_por = usuario
        periodo.save()
    return periodo


def _transicionar(periodo, destino, usuario=None):
    permitidos = TRANSICIONES_PERMITIDAS.get(periodo.estado, set())
    if destino not in permitidos:
        raise ValidationError(
            f"No se puede pasar de {periodo.get_estado_display()} a "
            f"{Estado(destino).label}."
        )
    periodo.estado = destino
    if usuario is not None:
        periodo.actualizado_por = usuario
    periodo.save()
    return periodo


def _validar_liquidaciones_para_cierre(periodo):
    qs = periodo.liquidaciones.exclude(
        estado=LiquidacionMensual.Estado.ANULADA
    )
    if qs.filter(estado=LiquidacionMensual.Estado.BORRADOR).exists():
        raise ValidationError(
            "No se puede cerrar el período: hay liquidaciones en borrador."
        )
    if qs.filter(requiere_recalculo=True).exists():
        raise ValidationError(
            "No se puede cerrar el período: hay liquidaciones sin recalcular."
        )
