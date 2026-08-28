from datetime import date
from decimal import Decimal
from django.test import TestCase
from finanzas.anuales import filas_exportacion_finanzas, matriz_por_categoria, reporte_anual, totales_por_origen
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero

class FIN007Tests(TestCase):
    def test_reporte_anual_matriz_y_origen(self):
        ingreso = CategoriaFinanciera.objects.get(codigo="ING_OTROS")
        egreso = CategoriaFinanciera.objects.get(codigo="EGR_BANCARIOS")
        MovimientoFinanciero.objects.create(fecha=date(2026, 1, 10), tipo="INGRESO", categoria=ingreso, descripcion="Ingreso", monto=100, origen="MANUAL")
        MovimientoFinanciero.objects.create(fecha=date(2026, 1, 11), tipo="EGRESO", categoria=egreso, descripcion="Banco", monto=40, origen="MANUAL")
        reporte = reporte_anual(2026)
        self.assertEqual(reporte["resultado"], Decimal("60"))
        self.assertEqual(reporte["meses"][0]["saldo_final"], Decimal("60"))
        self.assertTrue(reporte["meses"][0]["tiene_datos"])
        self.assertEqual(len(matriz_por_categoria(2026)), 2)
        self.assertEqual(totales_por_origen(2026)[0]["origen"], "MANUAL")
        self.assertEqual(len(filas_exportacion_finanzas(2026)), 12)
