from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from rendiciones.models import Rendicion
from rendiciones.services.estados import (
    acciones_disponibles,
    anular,
    aprobar,
    presentar,
    reabrir,
    rechazar,
)
from rendiciones.services.rendiciones import agregar_detalle
from rrhh.models import Trabajador

User = get_user_model()


class FlujoEstadoServicioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren5", password="clave")
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Materiales",
            total_declarado=Decimal("100000.00"),
        )
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="100000")

    def test_borrador_a_aprobada_invalido(self):
        with self.assertRaises(ValidationError):
            aprobar(self.rendicion, usuario=self.user)

    def test_borrador_a_presentada_ok(self):
        presentar(self.rendicion, usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.PRESENTADA)

    def test_presentada_a_aprobada_ok(self):
        presentar(self.rendicion, usuario=self.user)
        aprobar(self.rendicion, usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.APROBADA)

    def test_aprobada_a_borrador_invalido(self):
        presentar(self.rendicion, usuario=self.user)
        aprobar(self.rendicion, usuario=self.user)
        with self.assertRaises(ValidationError):
            reabrir(self.rendicion, usuario=self.user)

    def test_rechazar_exige_motivo(self):
        presentar(self.rendicion, usuario=self.user)
        with self.assertRaises(ValidationError):
            rechazar(self.rendicion, motivo="", usuario=self.user)

    def test_rechazar_y_reabrir(self):
        presentar(self.rendicion, usuario=self.user)
        rechazar(self.rendicion, motivo="Falta boleta", usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.RECHAZADA)
        self.assertEqual(self.rendicion.motivo_rechazo, "Falta boleta")
        acciones = acciones_disponibles(self.rendicion)
        self.assertFalse(acciones["editar"])
        self.assertTrue(acciones["reabrir"])
        reabrir(self.rendicion, usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.BORRADOR)
        self.assertTrue(acciones_disponibles(self.rendicion)["editar"])

    def test_anular_presentada_con_motivo(self):
        presentar(self.rendicion, usuario=self.user)
        anular(self.rendicion, motivo="Duplicada", usuario=self.user)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.ANULADA)
        self.assertIn("Duplicada", self.rendicion.observaciones)


class FlujoEstadoVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren5ui", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="rendiciones",
            codename__in=[
                "view_rendicion",
                "change_rendicion",
                "presentar_rendicion",
                "aprobar_rendicion",
                "rechazar_rendicion",
                "anular_rendicion",
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
            total_declarado=Decimal("50000.00"),
        )
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="50000")

    def test_ciclo_presentar_aprobar(self):
        self.client.post(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.PRESENTADA)
        response = self.client.post(
            reverse("rendiciones:rendicion_aprobar", args=[self.rendicion.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.APROBADA)

    def test_rechazar_y_reabrir_por_vista(self):
        self.client.post(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        response = self.client.post(
            reverse("rendiciones:rendicion_rechazar", args=[self.rendicion.pk]),
            {"motivo": "Montos incorrectos"},
        )
        self.assertEqual(response.status_code, 302)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.RECHAZADA)
        self.client.post(
            reverse("rendiciones:rendicion_reabrir", args=[self.rendicion.pk]),
            {"motivo": "Corregir antecedentes"},
        )
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.BORRADOR)

    def test_get_no_aprueba(self):
        self.client.post(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        self.client.get(
            reverse("rendiciones:rendicion_aprobar", args=[self.rendicion.pk])
        )
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.PRESENTADA)

    def test_ficha_muestra_acciones_presentada(self):
        self.client.post(
            reverse("rendiciones:rendicion_presentar", args=[self.rendicion.pk])
        )
        response = self.client.get(
            reverse("rendiciones:rendicion_detalle", args=[self.rendicion.pk])
        )
        self.assertContains(response, "Aprobar")
        self.assertContains(response, "Rechazar")
        self.assertNotContains(response, "Distribuir")
