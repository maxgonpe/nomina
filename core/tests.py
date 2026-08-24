from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from core.validators import formatear_rut, normalizar_rut, validar_rut


class ValidadorRutCoreTests(SimpleTestCase):
    def test_normaliza_y_formatea(self):
        self.assertEqual(normalizar_rut("18.651.495-5"), "186514955")
        self.assertEqual(formatear_rut("186514955"), "18.651.495-5")

    def test_dv_k(self):
        validar_rut("16.287.425-K")

    def test_dv_incorrecto(self):
        with self.assertRaises(ValidationError):
            validar_rut("1-1")
