from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from impuestos.models import PeriodoImpuesto
from impuestos.services import cerrar_periodo, periodos_pendientes, reabrir_periodo, validar_periodo


class IMP001Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="impuestos", password="clave")
        self.periodo = PeriodoImpuesto.objects.create(anio=2026, mes=2)

    def test_calcula_fechas_del_mes(self):
        self.assertEqual(str(self.periodo.fecha_inicio), "2026-02-01")
        self.assertEqual(str(self.periodo.fecha_fin), "2026-02-28")

    def test_periodo_unico_por_anio_mes(self):
        with self.assertRaises(Exception):
            PeriodoImpuesto.objects.create(anio=2026, mes=2)

    def test_flujo_validar_cerrar_y_reabrir(self):
        self.periodo.estado = PeriodoImpuesto.Estado.CALCULADO
        self.periodo.save(update_fields=["estado"])
        validar_periodo(self.periodo)
        cerrar_periodo(self.periodo, self.user)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, PeriodoImpuesto.Estado.CERRADO)
        self.assertEqual(self.periodo.cerrado_por, self.user)
        reabrir_periodo(self.periodo, self.user)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, PeriodoImpuesto.Estado.BORRADOR)

    def test_no_cierra_periodo_no_validado(self):
        with self.assertRaises(ValidationError):
            cerrar_periodo(self.periodo, self.user)

    def test_periodos_pendientes_excluye_cerrados(self):
        self.assertIn(self.periodo, periodos_pendientes())
