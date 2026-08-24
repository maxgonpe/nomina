from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.validators import formatear_rut, normalizar_rut, validar_rut
from rrhh.models import Trabajador
from rrhh.services.trabajadores import desactivar_trabajador

User = get_user_model()


class ValidadorRutTests(TestCase):
    def test_normaliza_formatos(self):
        self.assertEqual(normalizar_rut("18.651.495-5"), "186514955")
        self.assertEqual(normalizar_rut("18651495-5"), "186514955")
        self.assertEqual(normalizar_rut("16.287.425-k"), "16287425K")

    def test_formatea(self):
        self.assertEqual(formatear_rut("186514955"), "18.651.495-5")
        self.assertEqual(formatear_rut("16287425K"), "16.287.425-K")

    def test_acepta_rut_valido(self):
        validar_rut("18.651.495-5")
        validar_rut("16.287.425-K")

    def test_rechaza_dv_invalido(self):
        with self.assertRaises(ValidationError):
            validar_rut("18.651.495-4")

    def test_rechaza_vacio(self):
        with self.assertRaises(ValidationError):
            validar_rut("")


class TrabajadorModeloTests(TestCase):
    def test_crea_trabajador_normalizando_rut(self):
        t = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="  Ana Pérez  ",
        )
        self.assertEqual(t.rut_normalizado, "186514955")
        self.assertEqual(t.nombre_completo, "Ana Pérez")
        self.assertTrue(t.activo)

    def test_rechaza_rut_duplicado(self):
        Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        t2 = Trabajador(rut="18651495-5", nombre_completo="Otra")
        with self.assertRaises(ValidationError):
            t2.full_clean()

    def test_desactivar_conserva_registro(self):
        t = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        desactivar_trabajador(t)
        t.refresh_from_db()
        self.assertFalse(t.activo)
        self.assertEqual(Trabajador.objects.count(), 1)


class TrabajadorVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="rrhh",
            codename__in=[
                "view_trabajador",
                "add_trabajador",
                "change_trabajador",
                "delete_trabajador",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

    def test_anonimo_redirige_a_login(self):
        self.client.logout()
        url = reverse("rrhh:trabajador_lista")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_crea_trabajador_por_formulario(self):
        url = reverse("rrhh:trabajador_crear")
        response = self.client.post(
            url,
            {
                "rut": "18.651.495-5",
                "nombre_completo": "Ana Pérez",
                "activo": "on",
                "observaciones": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        t = Trabajador.objects.get()
        self.assertEqual(t.rut_normalizado, "186514955")
        self.assertEqual(t.creado_por, self.user)

    def test_formulario_rechaza_rut_duplicado(self):
        Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        response = self.client.post(
            reverse("rrhh:trabajador_crear"),
            {
                "rut": "18651495-5",
                "nombre_completo": "Duplicada",
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Trabajador.objects.count(), 1)
        self.assertContains(response, "Ya existe un trabajador")

    def test_listado_oculta_inactivos_por_defecto(self):
        Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Activa",
        )
        inactivo = Trabajador.objects.create(
            rut="16.287.425-K",
            nombre_completo="Luis Inactivo",
        )
        desactivar_trabajador(inactivo)
        response = self.client.get(reverse("rrhh:trabajador_lista"))
        self.assertContains(response, "Ana Activa")
        self.assertNotContains(response, "Luis Inactivo")

    def test_desactivar_por_vista(self):
        t = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        url = reverse("rrhh:trabajador_desactivar", args=[t.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        t.refresh_from_db()
        self.assertFalse(t.activo)
