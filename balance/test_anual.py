from datetime import date
from decimal import Decimal

from django.test import TestCase

from balance.anual import comparar_periodos, reporte_anual
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero


class BalanceAnualTests(TestCase):
    def test_reporte_mensual_y_total(self):
        categoria = CategoriaFinanciera.objects.get(codigo="ING_CLIENTES")
        MovimientoFinanciero.objects.create(fecha=date(2026, 2, 3), tipo="INGRESO", categoria=categoria, descripcion="Venta", monto=100)
        reporte = reporte_anual(2026)
        self.assertEqual(reporte["meses"][1]["resultado"], Decimal("100"))
        self.assertEqual(reporte["total_resultado"], Decimal("100"))

    def test_comparativo_entrega_diferencias(self):
        resultado = comparar_periodos(2025, 2026)
        self.assertEqual(resultado["diferencia_resultado"], Decimal("0"))
