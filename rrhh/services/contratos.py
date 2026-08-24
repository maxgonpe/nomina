from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q

from rrhh.models import AnexoContrato, Contrato


@dataclass
class CondicionLaboral:
    contrato: Contrato
    cargo: object
    centro_costo: object
    sueldo_base: Decimal
    anexo: AnexoContrato | None = None


def contrato_en_fecha(trabajador, fecha):
    qs = (
        Contrato.objects.filter(
            trabajador=trabajador,
            fecha_inicio__lte=fecha,
        )
        .filter(Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=fecha))
        .select_related("cargo", "centro_costo", "trabajador")
        .order_by("-fecha_inicio")
    )
    vigentes = [c for c in qs if c.estado == Contrato.Estado.VIGENTE]
    if vigentes:
        return vigentes[0]
    return qs.first()


def condicion_vigente(trabajador, fecha):
    """
    Sueldo, cargo y centro de costo a una fecha:
    condición inicial del contrato + anexos con fecha_vigencia <= fecha.
    """
    contrato = contrato_en_fecha(trabajador, fecha)
    if contrato is None:
        return None

    cargo = contrato.cargo
    centro_costo = contrato.centro_costo
    sueldo = contrato.sueldo_base_inicial
    ultimo = None

    anexos = (
        contrato.anexos.filter(fecha_vigencia__lte=fecha)
        .select_related("nuevo_cargo", "nuevo_centro_costo")
        .order_by("fecha_vigencia", "id")
    )
    for anexo in anexos:
        if anexo.nuevo_sueldo_base is not None:
            sueldo = anexo.nuevo_sueldo_base
        if anexo.nuevo_cargo_id:
            cargo = anexo.nuevo_cargo
        if anexo.nuevo_centro_costo_id:
            centro_costo = anexo.nuevo_centro_costo
        ultimo = anexo

    return CondicionLaboral(
        contrato=contrato,
        cargo=cargo,
        centro_costo=centro_costo,
        sueldo_base=sueldo,
        anexo=ultimo,
    )
