from datetime import date

from django.test import TestCase

from balance.cierres import cerrar_balance, huella_cierre, reabrir_balance
from balance.models import CierreBalance


class BalanceCierreTests(TestCase):
    def test_cierre_guarda_snapshot_y_huella(self):
        cierre = cerrar_balance(date(2026, 8, 31))
        self.assertEqual(cierre.estado, "CERRADO")
        self.assertTrue(huella_cierre(cierre))

    def test_reapertura_es_explicita(self):
        cierre = cerrar_balance(date(2026, 9, 30))
        reabrir_balance(cierre)
        self.assertEqual(CierreBalance.objects.get(pk=cierre.pk).estado, "REABIERTO")
