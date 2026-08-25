from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from rendiciones.models import Rendicion
from rendiciones.services.rendiciones import anular
from rrhh.models import Trabajador

User = get_user_model()


class RendicionModeloTests(TestCase):
    def setUp(self):
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )

    def test_crea_en_borrador_con_totales_cero(self):
        r = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Compra de materiales",
            total_declarado=Decimal("385000.00"),
        )
        self.assertEqual(r.estado, Rendicion.Estado.BORRADOR)
        self.assertEqual(r.total_distribuido, Decimal("0.00"))
        self.assertEqual(r.diferencia, Decimal("385000.00"))
        self.assertFalse(r.cuadra)

    def test_rechaza_total_negativo_en_bd(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Rendicion.objects.create(
                trabajador=self.trabajador,
                fecha=date(2026, 8, 12),
                descripcion="Inválida",
                total_declarado=Decimal("-1.00"),
            )


class RendicionServicioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren", password="clave")
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Combustible",
            total_declarado=Decimal("10000.00"),
            creado_por=self.user,
        )

    def test_anular_borrador(self):
        anular(self.rendicion, usuario=self.user, motivo="Error de carga")
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.estado, Rendicion.Estado.ANULADA)
        self.assertIn("Error de carga", self.rendicion.observaciones)
        self.assertEqual(self.rendicion.actualizado_por, self.user)
        self.assertEqual(Rendicion.objects.count(), 1)

    def test_no_anula_si_no_es_borrador(self):
        self.rendicion.estado = Rendicion.Estado.PRESENTADA
        self.rendicion.save(update_fields=["estado"])
        with self.assertRaises(ValidationError):
            anular(self.rendicion, usuario=self.user)


class RendicionVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("renui", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="rendiciones",
            codename__in=[
                "view_rendicion",
                "add_rendicion",
                "change_rendicion",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.inactivo = Trabajador.objects.create(
            rut="16.287.425-K",
            nombre_completo="Luis Inactivo",
            activo=False,
        )

    def test_anonimo_redirige_a_login(self):
        self.client.logout()
        response = self.client.get(reverse("rendiciones:rendicion_lista"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/", response.url)

    def test_crea_rendicion_valida(self):
        response = self.client.post(
            reverse("rendiciones:rendicion_crear"),
            {
                "trabajador": self.trabajador.pk,
                "fecha": "2026-08-12",
                "descripcion": "Compra de materiales y combustible",
                "total_declarado": "385000.00",
                "observaciones": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        r = Rendicion.objects.get()
        self.assertEqual(r.estado, Rendicion.Estado.BORRADOR)
        self.assertEqual(r.total_declarado, Decimal("385000.00"))
        self.assertEqual(r.creado_por, self.user)
        self.assertEqual(r.actualizado_por, self.user)

    def test_rechaza_monto_negativo(self):
        response = self.client.post(
            reverse("rendiciones:rendicion_crear"),
            {
                "trabajador": self.trabajador.pk,
                "fecha": "2026-08-12",
                "descripcion": "Inválida",
                "total_declarado": "-10",
                "observaciones": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Rendicion.objects.count(), 0)
        self.assertContains(response, "no puede ser negativo")

    def test_rechaza_trabajador_inexistente(self):
        response = self.client.post(
            reverse("rendiciones:rendicion_crear"),
            {
                "trabajador": 99999,
                "fecha": "2026-08-12",
                "descripcion": "Sin trabajador",
                "total_declarado": "100",
                "observaciones": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Rendicion.objects.count(), 0)

    def test_rechaza_trabajador_inactivo_en_alta(self):
        response = self.client.post(
            reverse("rendiciones:rendicion_crear"),
            {
                "trabajador": self.inactivo.pk,
                "fecha": "2026-08-12",
                "descripcion": "No debe pasar",
                "total_declarado": "100",
                "observaciones": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Rendicion.objects.count(), 0)

    def test_editar_borrador(self):
        r = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Original",
            total_declarado=Decimal("1000.00"),
        )
        response = self.client.post(
            reverse("rendiciones:rendicion_editar", args=[r.pk]),
            {
                "trabajador": self.trabajador.pk,
                "fecha": "2026-08-15",
                "descripcion": "Actualizada",
                "total_declarado": "2000.00",
                "observaciones": "Nota",
            },
        )
        self.assertEqual(response.status_code, 302)
        r.refresh_from_db()
        self.assertEqual(r.descripcion, "Actualizada")
        self.assertEqual(r.total_declarado, Decimal("2000.00"))
        self.assertEqual(r.fecha, date(2026, 8, 15))
        self.assertEqual(r.actualizado_por, self.user)

    def test_listar_y_filtrar_trabajador(self):
        otro = Trabajador.objects.create(
            rut="11.111.111-1",
            nombre_completo="Otro",
        )
        Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 1),
            descripcion="De Ana",
            total_declarado=Decimal("100"),
        )
        Rendicion.objects.create(
            trabajador=otro,
            fecha=date(2026, 8, 2),
            descripcion="De Otro",
            total_declarado=Decimal("200"),
        )
        response = self.client.get(
            reverse("rendiciones:rendicion_lista"),
            {"trabajador": self.trabajador.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "De Ana")
        self.assertNotContains(response, "De Otro")

    def test_detalle_muestra_auditoria(self):
        r = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Con auditoría",
            total_declarado=Decimal("500"),
            creado_por=self.user,
            actualizado_por=self.user,
        )
        response = self.client.get(
            reverse("rendiciones:rendicion_detalle", args=[r.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Con auditoría")
        self.assertContains(response, "renui")
        self.assertContains(response, "Borrador")
