from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from remuneraciones.models import (
    ConceptoRemuneracion,
    LiquidacionMensual,
    MovimientoRemuneracion,
    marcar_liquidacion_pendiente_recalculo,
)
from rrhh.services.contratos import condicion_vigente

TWOPLACES = Decimal("0.01")


def dinero(valor):
    if valor is None:
        return None
    return Decimal(str(valor)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def conceptos_carga_manual():
    """
    Haberes y descuentos que se ingresan a mano (bonos, aguinaldo, anticipo).
    SUELDO_BASE, HORAS_EXTRA, FINIQUITO e INASISTENCIA no se cargan aquí.
    """
    return ConceptoRemuneracion.objects.filter(
        activo=True,
        editable=True,
        tipo__in=[
            ConceptoRemuneracion.Tipo.HABER,
            ConceptoRemuneracion.Tipo.DESCUENTO,
        ],
    ).order_by("orden", "nombre")


def condicion_en_periodo(trabajador, periodo):
    return (
        condicion_vigente(trabajador, periodo.fecha_fin)
        or condicion_vigente(trabajador, periodo.fecha_inicio)
    )


def obtener_o_crear_liquidacion_borrador(trabajador, periodo, usuario=None):
    """
    El movimiento cuelga de una liquidación. Si aún no existe (REM005 no
    corrió), se abre un borrador con el contrato vigente. Los totales los
    calcula el motor más adelante.
    """
    periodo.assert_editable()
    existente = LiquidacionMensual.objects.filter(
        trabajador=trabajador,
        periodo=periodo,
    ).select_related("contrato").first()
    if existente:
        if existente.estado == LiquidacionMensual.Estado.ANULADA:
            raise ValidationError(
                "La liquidación de este trabajador en el período está anulada. "
                "No se pueden registrar movimientos."
            )
        return existente

    condicion = condicion_en_periodo(trabajador, periodo)
    if condicion is None:
        raise ValidationError(
            "El trabajador no tiene contrato vigente en este período. "
            "No se puede crear la liquidación borrador para el movimiento."
        )

    cargo = condicion.cargo
    centro = condicion.centro_costo
    liquidacion = LiquidacionMensual(
        periodo=periodo,
        trabajador=trabajador,
        contrato=condicion.contrato,
        estado=LiquidacionMensual.Estado.BORRADOR,
        sueldo_base_snapshot=condicion.sueldo_base,
        cargo_codigo_snapshot=getattr(cargo, "codigo", "") or "",
        cargo_nombre_snapshot=getattr(cargo, "nombre", "") or "",
        centro_costo=centro,
        centro_costo_codigo_snapshot=getattr(centro, "codigo", "") or "",
        centro_costo_nombre_snapshot=getattr(centro, "nombre", "") or "",
        requiere_recalculo=True,
        creado_por=usuario,
        actualizado_por=usuario,
    )
    liquidacion.full_clean()
    liquidacion.save()
    return liquidacion


def validar_concepto_manual(concepto):
    if concepto is None:
        raise ValidationError({"concepto": "Debe elegir un concepto."})
    if concepto.tipo == ConceptoRemuneracion.Tipo.INFORMATIVO:
        raise ValidationError(
            {
                "concepto": (
                    "Un concepto informativo no se carga como movimiento "
                    "de haber o descuento."
                )
            }
        )
    if not concepto.editable:
        raise ValidationError(
            {
                "concepto": (
                    f"{concepto.codigo} lo genera el sistema "
                    "(sueldo, horas extra, finiquito o inasistencia). "
                    "No se ingresa a mano."
                )
            }
        )
    if not concepto.activo:
        raise ValidationError(
            {"concepto": "Ese concepto está desactivado."}
        )


def monto_desde_cantidad(cantidad, valor_unitario, monto):
    if cantidad is not None and valor_unitario is not None:
        calculado = dinero(
            Decimal(str(cantidad)) * Decimal(str(valor_unitario))
        )
        if monto is None:
            return calculado
        if dinero(monto) != calculado:
            raise ValidationError(
                {
                    "monto": (
                        "El monto no coincide con cantidad × valor unitario "
                        f"({calculado})."
                    )
                }
            )
        return calculado
    if monto is None:
        raise ValidationError({"monto": "El monto es obligatorio."})
    return dinero(monto)


def registrar_movimiento(
    *,
    trabajador,
    periodo,
    concepto,
    monto,
    cantidad=None,
    valor_unitario=None,
    descripcion="",
    origen=None,
    usuario=None,
    instance=None,
):
    """
    Alta o edición de un movimiento. El signo contable lo da concepto.tipo,
    nunca el texto del usuario. monto siempre es positivo.
    """
    periodo.assert_editable()
    validar_concepto_manual(concepto)
    monto = monto_desde_cantidad(cantidad, valor_unitario, monto)
    if monto is None or monto <= 0:
        raise ValidationError({"monto": "El monto debe ser mayor que 0."})

    origen = origen or MovimientoRemuneracion.Origen.MANUAL
    with transaction.atomic():
        if instance is not None and instance.pk:
            movimiento = instance
            if movimiento.bloqueado:
                raise ValidationError(
                    "Este movimiento está bloqueado y no se puede editar."
                )
            liquidacion = movimiento.liquidacion
            if (
                liquidacion.trabajador_id != trabajador.pk
                or liquidacion.periodo_id != periodo.pk
            ):
                liquidacion = obtener_o_crear_liquidacion_borrador(
                    trabajador, periodo, usuario=usuario
                )
        else:
            liquidacion = obtener_o_crear_liquidacion_borrador(
                trabajador, periodo, usuario=usuario
            )
            movimiento = MovimientoRemuneracion()

        movimiento.liquidacion = liquidacion
        movimiento.concepto = concepto
        movimiento.cantidad = cantidad
        movimiento.valor_unitario = valor_unitario
        movimiento.monto = monto
        movimiento.origen = origen
        movimiento.descripcion = descripcion or ""
        movimiento.generado_automaticamente = (
            origen == MovimientoRemuneracion.Origen.CALCULADO
        )
        if usuario is not None:
            if not movimiento.pk:
                movimiento.creado_por = usuario
            movimiento.actualizado_por = usuario
        movimiento.full_clean()
        movimiento.save()
    return movimiento


def eliminar_movimiento(movimiento):
    if movimiento.bloqueado:
        raise ValidationError(
            "Este movimiento está bloqueado y no se puede borrar."
        )
    movimiento.delete()


def suma_movimientos(trabajador, periodo, tipo=None):
    """Insumo de REM005: suma de montos (siempre positivos) por tipo."""
    qs = MovimientoRemuneracion.objects.filter(
        liquidacion__trabajador=trabajador,
        liquidacion__periodo=periodo,
    ).exclude(
        liquidacion__estado=LiquidacionMensual.Estado.ANULADA,
    )
    if tipo:
        qs = qs.filter(concepto__tipo=tipo)
    total = qs.aggregate(total=Sum("monto"))["total"]
    return total or Decimal("0.00")


def totales_movimientos_periodo(periodo):
    return (
        MovimientoRemuneracion.objects.filter(
            liquidacion__periodo=periodo,
        )
        .exclude(liquidacion__estado=LiquidacionMensual.Estado.ANULADA)
        .values(
            "liquidacion__trabajador_id",
            "liquidacion__trabajador__nombre_completo",
            "concepto__tipo",
        )
        .annotate(total=Sum("monto"))
        .order_by("liquidacion__trabajador__nombre_completo")
    )
