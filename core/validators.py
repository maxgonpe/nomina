import re

from django.core.exceptions import ValidationError


def normalizar_rut(valor):
    """
    Convierte:
        18.651.495-5
        18651495-5
        18 651 495-5

    en:
        186514955

    Mantiene K cuando corresponde.
    """
    if valor is None:
        return ""

    return re.sub(r"[^0-9kK]", "", str(valor)).upper()


def formatear_rut(valor):
    rut = normalizar_rut(valor)
    if len(rut) < 2:
        return valor or ""

    cuerpo = rut[:-1]
    dv = rut[-1]
    if not cuerpo.isdigit():
        return valor or ""

    cuerpo_fmt = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_fmt}-{dv}"


def validar_rut(valor):
    rut = normalizar_rut(valor)

    if len(rut) < 2:
        raise ValidationError("RUT inválido.")

    cuerpo = rut[:-1]
    dv_ingresado = rut[-1]

    if not cuerpo.isdigit():
        raise ValidationError("RUT inválido.")

    suma = 0
    multiplicador = 2

    for digito in reversed(cuerpo):
        suma += int(digito) * multiplicador
        multiplicador += 1

        if multiplicador > 7:
            multiplicador = 2

    resto = 11 - (suma % 11)

    if resto == 11:
        dv_calculado = "0"
    elif resto == 10:
        dv_calculado = "K"
    else:
        dv_calculado = str(resto)

    if dv_ingresado != dv_calculado:
        raise ValidationError("El dígito verificador del RUT no es válido.")
