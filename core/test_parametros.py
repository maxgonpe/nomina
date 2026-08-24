import inspect
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import ParametroNegocio, ParametroValor
from core.services.parametros import valor, valor_hora_extra

User = get_user_model()


class ParametroVigenciaTests(TestCase):
    def test_factor_he_2026(self):
        self.assertEqual(
            valor("FACTOR_HE", date(2026, 8, 1)),
            Decimal("0.0079545"),
        )

    def test_sin_vigencia_en_otra_fecha(self):
        with self.assertRaises(ValidationError):
            valor("FACTOR_HE", date(2025, 12, 31))

    def test_valor_hora_extra_consulta_parametro(self):
        sueldo = Decimal("800000")
        self.assertEqual(
            valor_hora_extra(sueldo, date(2026, 6, 15)),
            sueldo * Decimal("0.0079545"),
        )
        fuente = inspect.getsource(valor_hora_extra)
        self.assertNotIn("0.0079545", fuente)

    def test_rechaza_vigencias_superpuestas(self):
        parametro = ParametroNegocio.objects.get(codigo="FACTOR_HE")
        otro = ParametroValor(
            parametro=parametro,
            valor=Decimal("0.01"),
            vigencia_desde=date(2026, 6, 1),
            vigencia_hasta=date(2026, 7, 31),
        )
        with self.assertRaises(ValidationError):
            otro.full_clean()


class ParametroVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="core",
            codename__in=[
                "view_parametronegocio",
                "add_parametronegocio",
                "change_parametronegocio",
                "add_parametrovalor",
                "change_parametrovalor",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

    def test_lista_muestra_factor_he(self):
        response = self.client.get(reverse("core:parametro_lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FACTOR_HE")

    def test_alta_parametro_y_vigencia(self):
        response = self.client.post(
            reverse("core:parametro_crear"),
            {
                "codigo": "IVA",
                "nombre": "IVA",
                "descripcion": "Tasa IVA",
                "activo": "on",
            },
        )
        parametro = ParametroNegocio.objects.get(codigo="IVA")
        self.assertRedirects(
            response,
            reverse("core:parametro_detalle", args=[parametro.pk]),
        )
        self.client.post(
            reverse("core:parametro_valor_crear", args=[parametro.pk]),
            {
                "valor": "0.19",
                "vigencia_desde": "2026-01-01",
                "vigencia_hasta": "2026-12-31",
            },
        )
        self.assertEqual(
            valor("IVA", date(2026, 3, 1)),
            Decimal("0.19"),
        )
