from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from rendiciones.models import Rendicion, RendicionDetalle


def anular(rendicion, usuario=None, motivo=""):
    """
    Anula una rendición en BORRADOR (REN001).
    Transiciones formales del resto del flujo: REN005.
    """
    if rendicion.estado == Rendicion.Estado.ANULADA:
        raise ValidationError("La rendición ya está anulada.")
    if rendicion.estado != Rendicion.Estado.BORRADOR:
        raise ValidationError(
            "Solo se puede anular un borrador desde este módulo. "
            "El flujo completo de anulación se define en REN005."
        )
    rendicion.estado = Rendicion.Estado.ANULADA
    if motivo:
        texto = (rendicion.observaciones or "").strip()
        bloque = f"Anulación: {motivo.strip()}"
        rendicion.observaciones = f"{texto}\n{bloque}".strip() if texto else bloque
    if usuario is not None:
        rendicion.actualizado_por = usuario
    update_fields = ["estado", "observaciones", "actualizado_por", "actualizado_en"]
    rendicion.save(update_fields=update_fields)
    return rendicion


def puede_editar(rendicion):
    """Cabecera y detalles: BORRADOR (RECHAZADA se habilitará en REN005)."""
    return rendicion.estado == Rendicion.Estado.BORRADOR


def assert_puede_editar_detalles(rendicion):
    if not puede_editar(rendicion):
        raise ValidationError(
            "Solo se puede distribuir una rendición en borrador."
        )


def total_distribuido(rendicion):
    """Recalcula desde BD (propiedad del modelo; expuesta para servicios/tests)."""
    return rendicion.total_distribuido


def diferencia(rendicion):
    return rendicion.diferencia


@transaction.atomic
def guardar_distribucion(rendicion, formset, usuario=None):
    """Persiste el formset de detalles y actualiza auditoría de la cabecera."""
    assert_puede_editar_detalles(rendicion)
    if not formset.is_valid():
        raise ValidationError("La distribución tiene errores.")

    instancias = formset.save(commit=False)
    for detalle in instancias:
        if usuario is not None:
            if not detalle.pk:
                detalle.creado_por = usuario
            detalle.actualizado_por = usuario
        detalle.rendicion = rendicion
        detalle.full_clean()
        detalle.save()

    for detalle in formset.deleted_objects:
        detalle.delete()

    if usuario is not None:
        rendicion.actualizado_por = usuario
        rendicion.save(update_fields=["actualizado_por", "actualizado_en"])

    rendicion.refresh_from_db()
    return rendicion


def agregar_detalle(
    rendicion,
    *,
    centro_costo,
    monto,
    descripcion="",
    usuario=None,
):
    """Alta puntual de una línea (tests / endpoints auxiliares)."""
    assert_puede_editar_detalles(rendicion)
    if not centro_costo.activo:
        raise ValidationError(
            "Solo se pueden usar centros de costo activos en líneas nuevas."
        )
    monto = Decimal(monto)
    if monto <= 0:
        raise ValidationError("El monto debe ser mayor que cero.")
    detalle = RendicionDetalle(
        rendicion=rendicion,
        centro_costo=centro_costo,
        descripcion=(descripcion or "").strip(),
        monto=monto,
    )
    if usuario is not None:
        detalle.creado_por = usuario
        detalle.actualizado_por = usuario
    detalle.full_clean()
    detalle.save()
    if usuario is not None:
        rendicion.actualizado_por = usuario
        rendicion.save(update_fields=["actualizado_por", "actualizado_en"])
    return detalle
