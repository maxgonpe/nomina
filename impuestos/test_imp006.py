from datetime import date
from decimal import Decimal
from django.test import TestCase
from impuestos.models import PeriodoImpuesto, PagoImpuesto
from impuestos.reportes import filas_exportacion_impuestos, pagos_por_fecha, resumen_anual, resumen_periodo


class IMP006Tests(TestCase):
    def setUp(self):
        self.periodo = PeriodoImpuesto.objects.create(anio=2026, mes=8, estado=PeriodoImpuesto.Estado.VALIDADO, neto_ventas=1000, iva_ventas=190, iva_compras=50, subtotal_iva=140, total_ppm=10, tasa_ppm_snapshot="0.01", monto_a_pagar=150)

    def test_resumen_periodo_y_anual(self):
        PagoImpuesto.objects.create(periodo=self.periodo, fecha=date(2026, 9, 5), monto=50)
        resumen = resumen_periodo(self.periodo)
        self.assertEqual(resumen["total_determinado"], Decimal("150"))
        self.assertEqual(resumen["saldo"], Decimal("100"))
        self.assertEqual(resumen_anual(2026)["total_pagado"], Decimal("50"))

    def test_pago_se_filtra_por_fecha_real(self):
        pago = PagoImpuesto.objects.create(periodo=self.periodo, fecha=date(2026, 9, 5), monto=50)
        self.assertEqual(list(pagos_por_fecha(date(2026, 8, 1), date(2026, 8, 31))), [])
        self.assertEqual(list(pagos_por_fecha(date(2026, 9, 1), date(2026, 9, 30))), [pago])

    def test_exportacion_no_inventa_periodos(self):
        self.assertEqual(len(filas_exportacion_impuestos(2026)), 1)
