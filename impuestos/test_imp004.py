from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from core.models import ParametroNegocio, ParametroValor
from facturacion.models import Cliente, DocumentoTributario
from impuestos.determinacion import determinar_periodo, validar_determinacion
from impuestos.iva import calcular_iva_periodo
from impuestos.models import PeriodoImpuesto
from impuestos.ppm import calcular_ppm


class IMP004Tests(TestCase):
    def setUp(self):
        cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente determinación")
        DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 10), cliente=cliente, tipo_documento="FACTURA", numero="1", neto=1000, iva=190, total=1190)
        parametro = ParametroNegocio.objects.create(codigo="TASA_PPM", nombre="Tasa PPM")
        ParametroValor.objects.create(parametro=parametro, valor="0.01", vigencia_desde=date(2026, 1, 1))
        self.periodo = PeriodoImpuesto.objects.create(anio=2026, mes=8)

    def calcular_componentes(self):
        calcular_iva_periodo(self.periodo)
        calcular_ppm(self.periodo)
        self.periodo.refresh_from_db()

    def test_determina_iva_mas_ppm(self):
        self.calcular_componentes()
        resultado = determinar_periodo(self.periodo)
        self.assertEqual(resultado["iva_determinado"], Decimal("190"))
        self.assertEqual(resultado["ppm"], Decimal("10.00"))
        self.assertEqual(resultado["total_determinado"], Decimal("200.00"))

    def test_no_determina_sin_ppm(self):
        calcular_iva_periodo(self.periodo)
        with self.assertRaises(ValidationError):
            determinar_periodo(self.periodo)

    def test_valida_determinacion(self):
        self.calcular_componentes()
        determinar_periodo(self.periodo)
        validar_determinacion(self.periodo)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, PeriodoImpuesto.Estado.VALIDADO)
