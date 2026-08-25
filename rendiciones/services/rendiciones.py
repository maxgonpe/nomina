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


def puede_editar_documentos(rendicion):
    """Respaldos alterables solo en estados editables (REN004)."""
    return puede_editar(rendicion)


def assert_puede_editar_documentos(rendicion):
    if not puede_editar_documentos(rendicion):
        raise ValidationError(
            "No se pueden agregar ni eliminar documentos en este estado."
        )


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


def validar_cuadratura(rendicion):
    """
    Gate formal BORRADOR → PRESENTADA (REN003).
    Exige detalles, total_declarado > 0 y Decimal exacto.
    """
    errores = []
    if not rendicion.detalles.exists():
        errores.append("La rendición no tiene líneas de distribución.")
    if rendicion.total_declarado is None or rendicion.total_declarado <= Decimal("0.00"):
        errores.append(
            "El total declarado debe ser mayor que cero para presentar."
        )
    diff = diferencia(rendicion)
    if diff != Decimal("0.00"):
        errores.append(
            f"La rendición no cuadra: diferencia {diff}."
        )
    if errores:
        raise ValidationError(errores)
    return True


def puede_presentar(rendicion):
    if rendicion.estado != Rendicion.Estado.BORRADOR:
        return False
    try:
        validar_cuadratura(rendicion)
    except ValidationError:
        return False
    return True


@transaction.atomic
def presentar(rendicion, usuario=None):
    """Pasa BORRADOR → PRESENTADA solo si cuadra (REN003)."""
    if rendicion.estado != Rendicion.Estado.BORRADOR:
        raise ValidationError(
            "Solo una rendición en borrador puede presentarse."
        )
    validar_cuadratura(rendicion)
    rendicion.estado = Rendicion.Estado.PRESENTADA
    if usuario is not None:
        rendicion.actualizado_por = usuario
    rendicion.save(update_fields=["estado", "actualizado_por", "actualizado_en"])
    return rendicion


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


@transaction.atomic
def agregar_documento(rendicion, *, tipo, archivo, descripcion="", usuario=None):
    from rendiciones.models import DocumentoRendicion

    assert_puede_editar_documentos(rendicion)
    doc = DocumentoRendicion(
        rendicion=rendicion,
        tipo=tipo,
        archivo=archivo,
        descripcion=(descripcion or "").strip(),
    )
    if usuario is not None:
        doc.creado_por = usuario
        doc.actualizado_por = usuario
    doc.full_clean()
    doc.save()
    if usuario is not None:
        rendicion.actualizado_por = usuario
        rendicion.save(update_fields=["actualizado_por", "actualizado_en"])
    return doc


@transaction.atomic
def eliminar_documento(documento, usuario=None):
    rendicion = documento.rendicion
    assert_puede_editar_documentos(rendicion)
    archivo = documento.archivo
    documento.delete()
    if archivo:
        archivo.delete(save=False)
    if usuario is not None:
        rendicion.actualizado_por = usuario
        rendicion.save(update_fields=["actualizado_por", "actualizado_en"])
    return rendicion
