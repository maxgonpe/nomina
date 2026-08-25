from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from rendiciones.models import Rendicion
from rendiciones.services.rendiciones import (
    agregar_detalle,
    presentar,
    validar_cuadratura,
)
from rrhh.models import Trabajador

User = get_user_model()


class CuadraturaServicioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren3", password="clave")
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.cga = CentroCosto.objects.create(codigo="CGA", nombre="CGA")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Materiales",
            total_declarado=Decimal("385000.00"),
        )

    def test_sin_detalles_rechaza(self):
        with self.assertRaises(ValidationError) as ctx:
            validar_cuadratura(self.rendicion)
        self.assertTrue(
            any("distribución" in m.lower() for m in ctx.exception.messages)
        )

    def test_descuadrada_rechaza(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="200000")
        with self.assertRaises(ValidationError) as ctx:
            validar_cuadratura(self.rendicion)
        self.assertTrue(
            any("no cuadra" in m.lower() for m in ctx.exception.messages)
        )

    def test_total_cero_rechaza(self):
        self.rendicion.total_declarado = Decimal("0.00")
        self.rendicion.save(update_fields=["total_declarado"])
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="0.01")
        # monto detalle > 0 pero declarado 0 → no cuadra y total<=0
        with self.assertRaises(ValidationError):
            validar_cuadratura(self.rendicion)

    def test_cuadrada_acepta_decimal_exacto(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="200000.00")
        agregar_detalle(self.rendicion, centro_costo=self.cga, monto="185000.00")
        self.assertTrue(validar_cuadratura(self.rendicion))
        self.assertEqual(self.rendicion.diferencia, Decimal("0.00"))
        self.assertIsInstance(self.rendicion.diferencia, Decimal)

    def test_presentar_cuadrada(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="385000.00")
        presentar(self.rendicion, usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.PRESENTADA)
        self.assertEqual(self.rendicion.actualizado_por, self.user)

    def test_presentar_descuadrada_rechaza(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="100")
        with self.assertRaises(ValidationError):
            presentar(self.rendicion, usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.BORRADOR)

    def test_estado_no_permitido_rechaza(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="385000")
        self.rendicion.estado = Rendicion.Estado.PRESENTADA
        self.rendicion.save(update_fields=["estado"])
        with self.assertRaises(ValidationError):
            presentar(self.rendicion, usuario=self.user)


class CuadraturaVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren3ui", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="rendiciones",
            codename__in=[
                "view_rendicion",
                "change_rendicion",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Combustible",
            total_declarado=Decimal("100000.00"),
        )

    def test_get_muestra_bloqueo_si_descuadrada(self):
        response = self.client.get(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No puede presentarse")
        self.assertNotContains(response, "Confirmar presentación")

    def test_post_no_cambia_si_descuadrada(self):
        response = self.client.post(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.BORRADOR)

    def test_post_presenta_si_cuadra(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="100000")
        response = self.client.post(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.PRESENTADA)

    def test_get_no_cambia_estado(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="100000")
        response = self.client.get(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La rendición cuadra")
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.BORRADOR)
