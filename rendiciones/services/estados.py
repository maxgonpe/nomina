"""Transiciones de estado de rendición (REN005)."""

from django.core.exceptions import ValidationError
from django.db import transaction

from rendiciones.models import Rendicion

ESTADOS_ANULABLES = (
    Rendicion.Estado.BORRADOR,
    Rendicion.Estado.PRESENTADA,
    Rendicion.Estado.RECHAZADA,
)


def acciones_disponibles(rendicion):
    """Qué acciones de flujo permiten el estado actual (sin mirar permisos)."""
    from rendiciones.services.rendiciones import puede_presentar

    estado = rendicion.estado
    return {
        "editar": estado == Rendicion.Estado.BORRADOR,
        "presentar": puede_presentar(rendicion),
        "aprobar": estado == Rendicion.Estado.PRESENTADA,
        "rechazar": estado == Rendicion.Estado.PRESENTADA,
        "reabrir": estado == Rendicion.Estado.RECHAZADA,
        "anular": estado in ESTADOS_ANULABLES,
    }


def _set_estado(rendicion, estado, usuario=None, extra_fields=None):
    rendicion.estado = estado
    fields = ["estado", "actualizado_por", "actualizado_en"]
    if usuario is not None:
        rendicion.actualizado_por = usuario
    if extra_fields:
        for nombre, valor in extra_fields.items():
            setattr(rendicion, nombre, valor)
            fields.append(nombre)
    seen = set()
    update_fields = []
    for f in fields:
        if f not in seen:
            seen.add(f)
            update_fields.append(f)
    rendicion.save(update_fields=update_fields)
    return rendicion


@transaction.atomic
def presentar(rendicion, usuario=None):
    """BORRADOR → PRESENTADA (exige cuadratura REN003)."""
    from rendiciones.services.rendiciones import validar_cuadratura

    if rendicion.estado != Rendicion.Estado.BORRADOR:
        raise ValidationError(
            "Solo una rendición en borrador puede presentarse."
        )
    validar_cuadratura(rendicion)
    return _set_estado(rendicion, Rendicion.Estado.PRESENTADA, usuario)


@transaction.atomic
def aprobar(rendicion, usuario=None):
    """PRESENTADA → APROBADA."""
    if rendicion.estado != Rendicion.Estado.PRESENTADA:
        raise ValidationError(
            "Solo una rendición presentada puede aprobarse."
        )
    return _set_estado(rendicion, Rendicion.Estado.APROBADA, usuario)


@transaction.atomic
def rechazar(rendicion, *, motivo, usuario=None):
    """PRESENTADA → RECHAZADA (motivo obligatorio)."""
    if rendicion.estado != Rendicion.Estado.PRESENTADA:
        raise ValidationError(
            "Solo una rendición presentada puede rechazarse."
        )
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo de rechazo es obligatorio.")
    return _set_estado(
        rendicion,
        Rendicion.Estado.RECHAZADA,
        usuario,
        extra_fields={"motivo_rechazo": motivo},
    )


@transaction.atomic
def reabrir(rendicion, usuario=None):
    """RECHAZADA → BORRADOR (acción explícita para volver a editar)."""
    if rendicion.estado != Rendicion.Estado.RECHAZADA:
        raise ValidationError(
            "Solo una rendición rechazada puede reabrirse a borrador."
        )
    return _set_estado(rendicion, Rendicion.Estado.BORRADOR, usuario)


@transaction.atomic
def anular(rendicion, *, motivo, usuario=None):
    """
    Anula desde BORRADOR, PRESENTADA o RECHAZADA.
    No anula APROBADA/PAGADA desde este módulo.
    """
    if rendicion.estado == Rendicion.Estado.ANULADA:
        raise ValidationError("La rendición ya está anulada.")
    if rendicion.estado not in ESTADOS_ANULABLES:
        raise ValidationError(
            "No se puede anular una rendición en este estado."
        )
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El motivo de anulación es obligatorio.")
    texto = (rendicion.observaciones or "").strip()
    bloque = f"Anulación: {motivo}"
    observaciones = f"{texto}\n{bloque}".strip() if texto else bloque
    return _set_estado(
        rendicion,
        Rendicion.Estado.ANULADA,
        usuario,
        extra_fields={"observaciones": observaciones},
    )
