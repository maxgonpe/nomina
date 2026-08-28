from datetime import date
from decimal import Decimal

from django.test import TestCase

from finanzas.flujo import flujo_mensual, resultado_operacional, totales_por_grupo
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero

class FIN001Tests(TestCase):
    def test_catalogo_inicial(self):
        self.assertTrue(CategoriaFinanciera.objects.filter(codigo="EGR_REMUNERACIONES", permite_manual=False).exists())
        self.assertTrue(CategoriaFinanciera.objects.filter(codigo="ING_CLIENTES", tipo="INGRESO").exists())

    def test_categoria_manual_explicita(self):
        categoria = CategoriaFinanciera.objects.create(codigo=" egr-bancos ", nombre="Bancos", tipo="EGRESO", permite_manual=True)
        self.assertEqual(categoria.codigo, "EGR-BANCOS")

    def test_catalogo_pre_bal02(self):
        aporte = CategoriaFinanciera.objects.get(codigo="ING_APORTE_CAPITAL")
        inversion = CategoriaFinanciera.objects.get(codigo="EGR_INVERSION")
        self.assertEqual(aporte.grupo_flujo, "FINANCIAMIENTO")
        self.assertFalse(aporte.afecta_resultado)
        self.assertEqual(inversion.grupo_flujo, "INVERSION")
        self.assertFalse(inversion.afecta_resultado)

    def test_separa_caja_resultado_y_grupos_de_flujo(self):
        cliente = CategoriaFinanciera.objects.get(codigo="ING_CLIENTES")
        operacion = CategoriaFinanciera.objects.get(codigo="EGR_PROVEEDORES")
        inversion = CategoriaFinanciera.objects.get(codigo="EGR_INVERSION")
        aporte = CategoriaFinanciera.objects.get(codigo="ING_APORTE_CAPITAL")
        datos = [
            ("INGRESO", cliente, 20000),
            ("EGRESO", operacion, 12000),
            ("EGRESO", inversion, 5000),
            ("INGRESO", aporte, 10000),
        ]
        for tipo, categoria, monto in datos:
            MovimientoFinanciero.objects.create(fecha=date(2026, 9, 10), tipo=tipo, categoria=categoria, descripcion=categoria.codigo, monto=monto)
        flujo = flujo_mensual(2026, 9)
        self.assertEqual(flujo["resultado"], Decimal("13000"))
        self.assertEqual(resultado_operacional(2026, 9), Decimal("8000"))
        grupos = {fila["grupo_flujo"]: fila for fila in totales_por_grupo(2026, 9)}
        self.assertEqual(grupos["OPERACION"]["resultado"], Decimal("8000"))
        self.assertEqual(grupos["INVERSION"]["resultado"], Decimal("0"))
        self.assertEqual(grupos["FINANCIAMIENTO"]["resultado"], Decimal("0"))

# Create your tests here.
