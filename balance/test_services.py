from datetime import date
from decimal import Decimal

from django.test import TestCase

from balance.services import balance_a_fecha
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero, ObligacionFinanciera


class BalanceServicesTests(TestCase):
    def test_balance_a_fecha_separa_caja_y_resultado(self):
        ingreso = CategoriaFinanciera.objects.get(codigo="ING_CLIENTES")
        aporte = CategoriaFinanciera.objects.get(codigo="ING_APORTE_CAPITAL")
        MovimientoFinanciero.objects.create(fecha=date(2026, 8, 10), tipo="INGRESO", categoria=ingreso, descripcion="Venta", monto=200)
        MovimientoFinanciero.objects.create(fecha=date(2026, 8, 11), tipo="INGRESO", categoria=aporte, descripcion="Aporte", monto=1000)
        resultado = balance_a_fecha(date(2026, 8, 31))
        self.assertEqual(resultado["caja"]["saldo"], Decimal("1200"))
        self.assertEqual(resultado["resultado_gestion"], Decimal("200"))

    def test_fecha_corte_excluye_movimientos_posteriores(self):
        categoria = CategoriaFinanciera.objects.get(codigo="ING_CLIENTES")
        MovimientoFinanciero.objects.create(fecha=date(2026, 9, 1), tipo="INGRESO", categoria=categoria, descripcion="Posterior", monto=500)
        resultado = balance_a_fecha(date(2026, 8, 31))
        self.assertEqual(resultado["caja"]["saldo"], Decimal("0"))
