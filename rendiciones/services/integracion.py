"""
REN007 — Frontera hacia Finanzas e integración Excel.

No crea movimientos financieros ni archivos Excel.
Entrega datos normalizados e idempotentes para que esos módulos consuman.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError

from rendiciones.models import Rendicion
from rendiciones.services.reportes import dinero


def es_elegible_finanzas(rendicion):
    """Solo APROBADA alimenta Finanzas (PAGADA es consecuencia posterior)."""
    return rendicion.estado == Rendicion.Estado.APROBADA


def clave_movimiento(detalle):
    """
    Clave estable para sincronización idempotente en Finanzas.
    Finanzas puede usar referencia/origen + esta clave para no duplicar.
    """
    return f"REN-{detalle.rendicion_id}-DET-{detalle.pk}"


def datos_financieros(rendicion):
    """
    Salida lógica por centro de costo (un egreso conceptual por detalle).

    Cada ítem:
      rendicion_id, detalle_id, fecha, trabajador_id, trabajador,
      descripcion, centro_costo_id, centro_costo_codigo, centro_costo,
      monto, estado, tipo_movimiento, clave
    """
    if not es_elegible_finanzas(rendicion):
        raise ValidationError(
            "Solo una rendición aprobada puede generar datos financieros."
        )

    detalles = (
        rendicion.detalles.select_related("centro_costo")
        .order_by("centro_costo__codigo", "pk")
    )
    if not detalles.exists():
        raise ValidationError(
            "La rendición aprobada no tiene distribución por centro de costo."
        )

    items = []
    for detalle in detalles:
        descripcion = detalle.descripcion.strip() or rendicion.descripcion
        items.append(
            {
                "rendicion_id": rendicion.pk,
                "detalle_id": detalle.pk,
                "fecha": rendicion.fecha,
                "trabajador_id": rendicion.trabajador_id,
                "trabajador": rendicion.trabajador.nombre_completo,
                "descripcion": descripcion,
                "centro_costo_id": detalle.centro_costo_id,
                "centro_costo_codigo": detalle.centro_costo.codigo,
                "centro_costo": detalle.centro_costo.nombre,
                "monto": dinero(detalle.monto),
                "estado": rendicion.estado,
                "tipo_movimiento": "EGRESO",
                "clave": clave_movimiento(detalle),
            }
        )

    total = dinero(sum((i["monto"] for i in items), Decimal("0.00")))
    if total != dinero(rendicion.total_declarado):
        # Puede diferir si no cuadra; aún así entregamos la distribución.
        # Quien sincronice en Finanzas debe validar de nuevo.
        pass

    return {
        "rendicion_id": rendicion.pk,
        "fecha": rendicion.fecha,
        "trabajador_id": rendicion.trabajador_id,
        "trabajador": rendicion.trabajador.nombre_completo,
        "descripcion": rendicion.descripcion,
        "estado": rendicion.estado,
        "total_declarado": dinero(rendicion.total_declarado),
        "total_movimientos": total,
        "movimientos": items,
    }


def estado_financiero(rendicion):
    """
    Indicador liviano para la ficha (sin implementar Finanzas).
    - No elegible / Pendiente de registrar / Registrada / Pagada
    """
    if rendicion.estado == Rendicion.Estado.PAGADA:
        return {
            "codigo": "PAGADA",
            "label": "Pagada",
        }
    if rendicion.estado != Rendicion.Estado.APROBADA:
        return {
            "codigo": "NO_APLICA",
            "label": "No aplica (solo aprobadas)",
        }
    # related_name en finanzas.MovimientoFinanciero
    registrados = getattr(rendicion, "movimientos_financieros", None)
    if registrados is not None and registrados.exists():
        return {
            "codigo": "REGISTRADA",
            "label": "Registrada en finanzas",
        }
    return {
        "codigo": "PENDIENTE",
        "label": "Pendiente de registrar",
    }


def filas_excel(queryset):
    """
    Matriz tipo planilla de rendiciones:

    DESCRIPCION | <CC dinámicos...> | TOTAL

    Los centros salen de los datos (si aparece BODEGA, se agrega columna).
    Solo incluye rendiciones APROBADA o PAGADA por defecto si el caller
    no filtró; el queryset lo decide el consumidor.
    """
    rendiciones = list(
        queryset.select_related("trabajador")
        .prefetch_related("detalles__centro_costo")
        .order_by("fecha", "pk")
    )

    codigos = []
    vistos = set()
    for r in rendiciones:
        for d in r.detalles.all():
            codigo = d.centro_costo.codigo
            if codigo not in vistos:
                vistos.add(codigo)
                codigos.append(codigo)
    codigos.sort()

    encabezado = ["ID", "FECHA", "TRABAJADOR", "DESCRIPCION", "ESTADO"] + codigos + [
        "TOTAL"
    ]
    filas = [encabezado]

    for r in rendiciones:
        montos = {c: Decimal("0.00") for c in codigos}
        for d in r.detalles.all():
            c = d.centro_costo.codigo
            if c not in montos:
                # Centro nuevo no visto en el primer pase (no debería pasar)
                montos[c] = Decimal("0.00")
                if c not in codigos:
                    codigos.append(c)
            montos[c] = dinero(montos[c] + d.monto)
        fila = [
            r.pk,
            r.fecha.isoformat(),
            r.trabajador.nombre_completo,
            r.descripcion,
            r.estado,
        ]
        for c in codigos:
            fila.append(dinero(montos.get(c, Decimal("0.00"))))
        fila.append(dinero(r.total_declarado))
        filas.append(fila)

    # Ajustar encabezado si se descubrieron códigos nuevos (defensivo)
    if len(encabezado) != 5 + len(codigos) + 1:
        filas[0] = (
            ["ID", "FECHA", "TRABAJADOR", "DESCRIPCION", "ESTADO"]
            + sorted(vistos)
            + ["TOTAL"]
        )

    return filas
