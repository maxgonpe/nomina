from django.core.exceptions import ValidationError

from rendiciones.models import Rendicion


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
    return rendicion.estado == Rendicion.Estado.BORRADOR
