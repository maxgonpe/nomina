from django.test import TestCase

from balance.models import LineaBalance


class LineaBalanceTests(TestCase):
    def test_catalogo_inicial_y_fuentes_declarativas(self):
        caja = LineaBalance.objects.get(codigo="CAJA")
        materiales = LineaBalance.objects.get(codigo="EXCEL_MATERIALES")
        self.assertEqual(caja.fuente, "FIN_SALDO")
        self.assertEqual(materiales.codigo_fuente, "MAT_MATERIALES")
        self.assertTrue(LineaBalance.objects.filter(codigo="CAPITAL_POR_ENTERAR", permite_ajuste=True).exists())

    def test_codigo_se_normaliza(self):
        linea = LineaBalance.objects.create(codigo=" nueva_linea ", nombre="Nueva", seccion="EXCEL", tipo="COMPRA", fuente="COM")
        self.assertEqual(linea.codigo, "NUEVA_LINEA")
