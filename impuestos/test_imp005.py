from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from impuestos.models import PeriodoImpuesto, PagoImpuesto
from impuestos.pagos import anular_pago, registrar_pago, situacion_pago


class IMP005Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="pagos", password="clave")
        self.periodo = PeriodoImpuesto.objects.create(anio=2026, mes=8, estado=PeriodoImpuesto.Estado.VALIDADO, monto_a_pagar=1000)

    def test_pagos_parciales_y_situacion(self):
        registrar_pago(PagoImpuesto(periodo=self.periodo, fecha=date(2026, 9, 1), monto=400))
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.total_pagado, Decimal("400"))
        self.assertEqual(self.periodo.saldo_pendiente, Decimal("600"))
        self.assertEqual(situacion_pago(self.periodo), "PARCIAL")

    def test_rechaza_sobrepago(self):
        with self.assertRaises(ValidationError):
            registrar_pago(PagoImpuesto(periodo=self.periodo, fecha=date(2026, 9, 1), monto=1001))

    def test_anulacion_recalcula_saldo(self):
        pago = PagoImpuesto.objects.create(periodo=self.periodo, fecha=date(2026, 9, 1), monto=400)
        anular_pago(pago, self.user, "Pago incorrecto")
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.total_pagado, Decimal("0.00"))
        self.assertEqual(situacion_pago(self.periodo), "PENDIENTE")
