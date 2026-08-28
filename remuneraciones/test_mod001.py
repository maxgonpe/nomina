from django.test import TestCase

from remuneraciones.forms import FiniquitoForm, MovimientoForm, PeriodoForm
from remuneraciones.models import ConceptoRemuneracion


class Mod001FormTest(TestCase):
    def test_formularios_no_exponen_estados_ni_derivados(self):
        self.assertNotIn("estado", PeriodoForm().fields)
        self.assertNotIn("estado", FiniquitoForm().fields)
        self.assertNotIn("monto_total", MovimientoForm().fields)

    def test_movimiento_manual_no_ofrece_concepto_solo_automatico(self):
        automatico = ConceptoRemuneracion.objects.create(
            codigo="CALCULADO_TEST",
            nombre="Calculado de prueba",
            tipo=ConceptoRemuneracion.Tipo.HABER,
            naturaleza_calculo=ConceptoRemuneracion.NaturalezaCalculo.AUTOMATICO,
            editable=True,
        )
        self.assertNotIn(automatico, MovimientoForm().fields["concepto"].queryset)
