from django.test import TestCase
from finanzas.models import CategoriaFinanciera

class FIN001Tests(TestCase):
    def test_catalogo_inicial(self):
        self.assertTrue(CategoriaFinanciera.objects.filter(codigo="EGR_REMUNERACIONES", permite_manual=False).exists())
        self.assertTrue(CategoriaFinanciera.objects.filter(codigo="ING_CLIENTES", tipo="INGRESO").exists())

    def test_categoria_manual_explicita(self):
        categoria = CategoriaFinanciera.objects.create(codigo=" egr-bancos ", nombre="Bancos", tipo="EGRESO", permite_manual=True)
        self.assertEqual(categoria.codigo, "EGR-BANCOS")

# Create your tests here.
