from datetime import date
from decimal import Decimal
from django.test import TestCase
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero
from finanzas.flujo import calcular_cierre, flujo_mensual

class FIN006Tests(TestCase):
    def setUp(self):
        self.ingreso = CategoriaFinanciera.objects.get(codigo="ING_OTROS")
        self.egreso = CategoriaFinanciera.objects.get(codigo="EGR_BANCARIOS")

    def test_flujo_mensual_y_saldo_inicial(self):
        MovimientoFinanciero.objects.create(fecha=date(2026, 7, 31), tipo="INGRESO", categoria=self.ingreso, descripcion="Anterior", monto=100)
        MovimientoFinanciero.objects.create(fecha=date(2026, 8, 2), tipo="INGRESO", categoria=self.ingreso, descripcion="Abono", monto=500)
        MovimientoFinanciero.objects.create(fecha=date(2026, 8, 3), tipo="EGRESO", categoria=self.egreso, descripcion="Banco", monto=150)
        MovimientoFinanciero.objects.create(fecha=date(2026, 8, 4), tipo="EGRESO", categoria=self.egreso, descripcion="Anulado", monto=999, anulado=True)
        flujo = flujo_mensual(2026, 8)
        self.assertEqual(flujo["saldo_inicial"], Decimal("100"))
        self.assertEqual(flujo["resultado"], Decimal("350"))
        self.assertEqual(flujo["saldo_final"], Decimal("450"))

    def test_calcula_cierre(self):
        from finanzas.models import CierreFinancieroMensual
        cierre = CierreFinancieroMensual.objects.create(anio=2026, mes=8)
        calcular_cierre(cierre)
        cierre.refresh_from_db()
        self.assertEqual(cierre.estado, "CALCULADO")
