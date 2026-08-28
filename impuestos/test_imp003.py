from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from core.models import ParametroNegocio, ParametroValor
from facturacion.models import Cliente, DocumentoTributario
from impuestos.models import PeriodoImpuesto
from impuestos.ppm import calcular_ppm


class IMP003Tests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente PPM")
        parametro = ParametroNegocio.objects.create(codigo="TASA_PPM", nombre="Tasa PPM")
        ParametroValor.objects.create(parametro=parametro, valor="0.0125", vigencia_desde=date(2026, 1, 1))
        self.periodo = PeriodoImpuesto.objects.create(anio=2026, mes=8)

    def test_calcula_y_guarda_snapshot(self):
        DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 10), cliente=self.cliente, tipo_documento="FACTURA", numero="1", neto=10000000, iva=1900000, total=11900000)
        resultado = calcular_ppm(self.periodo)
        self.assertEqual(resultado, {"base_ppm": Decimal("10000000"), "tasa_ppm": Decimal("0.0125"), "total_ppm": Decimal("125000.00")})
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.tasa_ppm_snapshot, Decimal("0.0125"))

    def test_sin_ventas_calcula_cero(self):
        self.assertEqual(calcular_ppm(self.periodo)["total_ppm"], Decimal("0.00"))

    def test_falla_sin_tasa(self):
        ParametroValor.objects.all().delete()
        with self.assertRaises(ValidationError):
            calcular_ppm(self.periodo)

    def test_no_recalcula_periodo_cerrado(self):
        self.periodo.estado = PeriodoImpuesto.Estado.CERRADO
        self.periodo.save(update_fields=["estado"])
        with self.assertRaises(ValidationError):
            calcular_ppm(self.periodo)
