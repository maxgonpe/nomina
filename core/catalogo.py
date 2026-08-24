from datetime import date
from decimal import Decimal

PARAMETROS_INICIALES = [
    {
        "codigo": "FACTOR_HE",
        "nombre": "Factor hora extra",
        "descripcion": (
            "Multiplicador del sueldo base para el valor de la hora extra. "
            "No hardcodear en fórmulas; consultar ParametroService.valor."
        ),
    },
    {
        "codigo": "VALOR_MOVILIZACION_MENSUAL",
        "nombre": "Valor mensual de movilización",
        "descripcion": "Monto mensual; se prorratea por días trabajados.",
    },
    {
        "codigo": "VALOR_COLACION_MENSUAL",
        "nombre": "Valor mensual de colación",
        "descripcion": "Monto mensual; se prorratea por días trabajados.",
    },
    {
        "codigo": "VALOR_DESGASTE_HERRAMIENTAS",
        "nombre": "Valor mensual de desgaste de herramientas",
        "descripcion": "Monto mensual; se prorratea por días trabajados.",
    },
]

VALORES_INICIALES = [
    {
        "codigo": "FACTOR_HE",
        "valor": Decimal("0.0079545"),
        "vigencia_desde": date(2026, 1, 1),
        "vigencia_hasta": date(2026, 12, 31),
        "observaciones": "Valor histórico 2026 tomado del Excel de remuneraciones.",
    },
]
