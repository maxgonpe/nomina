from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from remuneraciones.models import ConceptoRemuneracion, LiquidacionMensual

User = get_user_model()

CAMPOS_PROHIBIDOS_LIQUIDACION = {
    "aguinaldo",
    "alojamiento",
    "colacion",
    "mov",
    "bono_produccion",
    "anticipo",
    "prestamo",
    "bono_faena",
}


class ConceptoCatalogoTests(TestCase):
    def test_catalogo_inicial(self):
        self.assertTrue(
            ConceptoRemuneracion.objects.filter(codigo="SUELDO_BASE").exists()
        )
        self.assertTrue(
            ConceptoRemuneracion.objects.filter(codigo="ANTICIPO").exists()
        )
        self.assertEqual(
            ConceptoRemuneracion.objects.get(codigo="COLACION").tipo,
            ConceptoRemuneracion.Tipo.HABER,
        )

    def test_nuevo_haber_no_altera_liquidacion(self):
        campos_antes = {f.name for f in LiquidacionMensual._meta.get_fields()}
        self.assertTrue(
            CAMPOS_PROHIBIDOS_LIQUIDACION.isdisjoint(campos_antes)
        )
        ConceptoRemuneracion.objects.create(
            codigo="BONO_FAENA",
            nombre="Bono faena",
            tipo=ConceptoRemuneracion.Tipo.HABER,
        )
        campos_despues = {f.name for f in LiquidacionMensual._meta.get_fields()}
        self.assertEqual(campos_antes, campos_despues)
        self.assertTrue(
            ConceptoRemuneracion.objects.filter(codigo="BONO_FAENA").exists()
        )

    def test_desactivar_conserva_el_concepto(self):
        concepto = ConceptoRemuneracion.objects.get(codigo="AGUINALDO")
        concepto.activo = False
        concepto.save()
        self.assertFalse(
            ConceptoRemuneracion.objects.get(codigo="AGUINALDO").activo
        )
        self.assertEqual(
            ConceptoRemuneracion.objects.filter(codigo="AGUINALDO").count(),
            1,
        )


class ConceptoVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_conceptoremuneracion",
                "add_conceptoremuneracion",
                "change_conceptoremuneracion",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

    def test_lista_y_alta_bono_faena(self):
        response = self.client.get(reverse("remuneraciones:concepto_lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SUELDO_BASE")
        response = self.client.post(
            reverse("remuneraciones:concepto_crear"),
            {
                "codigo": "bono_faena",
                "nombre": "Bono faena",
                "tipo": ConceptoRemuneracion.Tipo.HABER,
                "naturaleza_calculo": ConceptoRemuneracion.NaturalezaCalculo.MANUAL,
                "orden": "85",
                "editable": "on",
                "activo": "on",
            },
        )
        self.assertRedirects(response, reverse("remuneraciones:concepto_lista"))
        creado = ConceptoRemuneracion.objects.get(codigo="BONO_FAENA")
        self.assertEqual(creado.tipo, ConceptoRemuneracion.Tipo.HABER)
        self.assertTrue(creado.activo)
