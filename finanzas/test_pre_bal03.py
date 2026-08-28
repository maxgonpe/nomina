from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from finanzas.models import CategoriaFinanciera, MovimientoFinanciero, ObligacionFinanciera, PagoObligacionFinanciera
from finanzas.obligaciones import anular_pago, registrar_pago, saldo, sincronizar_pago_obligacion, situacion


class PreBal03Tests(TestCase):
    def setUp(self):
        self.categoria = CategoriaFinanciera.objects.get(codigo="EGR_PAGO_FINANCIAMIENTO")
        self.obligacion = ObligacionFinanciera.objects.create(categoria=self.categoria, descripcion="Plan de pago X", fecha_inicio=date(2026, 9, 1), monto_total=6000)
        self.usuario = get_user_model().objects.create_user(username="auditor")

    def test_pago_parcial_actualiza_saldo_estado_y_movimiento(self):
        pago = registrar_pago(PagoObligacionFinanciera(obligacion=self.obligacion, fecha=date(2026, 9, 10), monto=2000))
        self.obligacion.refresh_from_db()
        self.assertEqual(saldo(self.obligacion), Decimal("4000"))
        self.assertEqual(situacion(self.obligacion), "PARCIAL")
        self.assertEqual(MovimientoFinanciero.objects.get(referencia=f"OBLIGACION_PAGO:{pago.pk}").monto, Decimal("2000"))

    def test_rechaza_sobrepago(self):
        with self.assertRaises(ValidationError):
            registrar_pago(PagoObligacionFinanciera(obligacion=self.obligacion, fecha=date(2026, 9, 10), monto=6001))

    def test_saldo_a_fecha_de_corte(self):
        registrar_pago(PagoObligacionFinanciera(obligacion=self.obligacion, fecha=date(2026, 9, 30), monto=2000))
        registrar_pago(PagoObligacionFinanciera(obligacion=self.obligacion, fecha=date(2026, 10, 1), monto=1000))
        self.assertEqual(self.obligacion.saldo_a_fecha(date(2026, 9, 30)), Decimal("4000"))
        self.assertEqual(self.obligacion.saldo_a_fecha(date(2026, 10, 31)), Decimal("3000"))

    def test_anulacion_no_suma_pago_ni_movimiento(self):
        pago = registrar_pago(PagoObligacionFinanciera(obligacion=self.obligacion, fecha=date(2026, 9, 10), monto=2000))
        anular_pago(pago, self.usuario, "Corrección")
        self.assertEqual(saldo(self.obligacion), Decimal("6000"))
        movimiento = MovimientoFinanciero.objects.get(referencia=f"OBLIGACION_PAGO:{pago.pk}")
        self.assertTrue(movimiento.anulado)

    def test_sincronizacion_es_idempotente(self):
        pago = PagoObligacionFinanciera.objects.create(obligacion=self.obligacion, fecha=date(2026, 9, 10), monto=2000)
        sincronizar_pago_obligacion(pago)
        sincronizar_pago_obligacion(pago)
        self.assertEqual(MovimientoFinanciero.objects.filter(referencia=f"OBLIGACION_PAGO:{pago.pk}").count(), 1)
