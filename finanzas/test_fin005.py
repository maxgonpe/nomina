from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from finanzas.models import CategoriaFinanciera, MovimientoFinanciero
from finanzas.manuales import anular_movimiento_manual, registrar_movimiento_manual

class FIN005Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="manual", password="clave")
        self.categoria = CategoriaFinanciera.objects.get(codigo="EGR_BANCARIOS")

    def test_registra_manual_solo_con_categoria_autorizada(self):
        movimiento = registrar_movimiento_manual(MovimientoFinanciero(fecha=date(2026, 8, 1), tipo="EGRESO", categoria=self.categoria, descripcion="Comisión bancaria", monto=Decimal("15000")))
        self.assertEqual(movimiento.origen, "MANUAL")

    def test_rechaza_categoria_automatica(self):
        categoria = CategoriaFinanciera.objects.get(codigo="EGR_PROVEEDORES")
        with self.assertRaises(ValidationError):
            registrar_movimiento_manual(MovimientoFinanciero(fecha=date(2026, 8, 1), tipo="EGRESO", categoria=categoria, descripcion="Duplicado", monto=10))

    def test_anula_con_motivo_y_auditoria(self):
        movimiento = registrar_movimiento_manual(MovimientoFinanciero(fecha=date(2026, 8, 1), tipo="EGRESO", categoria=self.categoria, descripcion="Banco", monto=10))
        anular_movimiento_manual(movimiento, self.user, "Registrado por error")
        movimiento.refresh_from_db()
        self.assertTrue(movimiento.anulado)
        self.assertEqual(movimiento.anulado_por, self.user)
