from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from rendiciones.models import Rendicion, RendicionDetalle
from rendiciones.services.rendiciones import agregar_detalle, diferencia, total_distribuido
from rrhh.models import Trabajador

User = get_user_model()


class DistribucionServicioTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren2", password="clave")
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.cga = CentroCosto.objects.create(codigo="CGA", nombre="CGA")
        self.ofi = CentroCosto.objects.create(codigo="OFI", nombre="Oficina")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Compra de materiales y combustible",
            total_declarado=Decimal("385000.00"),
        )

    def test_un_solo_centro(self):
        agregar_detalle(
            self.rendicion,
            centro_costo=self.egc,
            monto="385000.00",
            descripcion="Todo EGC",
            usuario=self.user,
        )
        self.assertEqual(total_distribuido(self.rendicion), Decimal("385000.00"))
        self.assertEqual(diferencia(self.rendicion), Decimal("0.00"))
        self.assertTrue(self.rendicion.cuadra)

    def test_multiples_centros(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="200000")
        agregar_detalle(self.rendicion, centro_costo=self.cga, monto="100000")
        agregar_detalle(self.rendicion, centro_costo=self.ofi, monto="85000")
        self.assertEqual(total_distribuido(self.rendicion), Decimal("385000.00"))
        self.assertEqual(diferencia(self.rendicion), Decimal("0.00"))

    def test_dos_lineas_mismo_cc(self):
        agregar_detalle(
            self.rendicion,
            centro_costo=self.egc,
            monto="120000",
            descripcion="Materiales",
        )
        agregar_detalle(
            self.rendicion,
            centro_costo=self.egc,
            monto="80000",
            descripcion="Combustible",
        )
        self.assertEqual(RendicionDetalle.objects.filter(centro_costo=self.egc).count(), 2)
        self.assertEqual(total_distribuido(self.rendicion), Decimal("200000.00"))
        self.assertEqual(diferencia(self.rendicion), Decimal("185000.00"))

    def test_monto_cero_rechazado(self):
        with self.assertRaises(ValidationError):
            agregar_detalle(self.rendicion, centro_costo=self.egc, monto="0")

    def test_monto_negativo_rechazado(self):
        with self.assertRaises(ValidationError):
            agregar_detalle(self.rendicion, centro_costo=self.egc, monto="-10")

    def test_cc_inactivo_en_alta(self):
        self.ofi.activo = False
        self.ofi.save(update_fields=["activo"])
        with self.assertRaises(ValidationError):
            agregar_detalle(self.rendicion, centro_costo=self.ofi, monto="100")


class DistribucionVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren2ui", password="clave-segura")
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
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.cga = CentroCosto.objects.create(codigo="CGA", nombre="CGA")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Materiales",
            total_declarado=Decimal("300000.00"),
        )

    def _post_formset(self, filas, initial=0):
        data = {
            "det-TOTAL_FORMS": str(len(filas)),
            "det-INITIAL_FORMS": str(initial),
            "det-MIN_NUM_FORMS": "0",
            "det-MAX_NUM_FORMS": "1000",
        }
        for i, fila in enumerate(filas):
            data[f"det-{i}-centro_costo"] = fila["centro_costo"]
            data[f"det-{i}-descripcion"] = fila.get("descripcion", "")
            data[f"det-{i}-monto"] = fila["monto"]
            data[f"det-{i}-id"] = fila.get("id", "")
            if fila.get("DELETE"):
                data[f"det-{i}-DELETE"] = "on"
        return self.client.post(
            reverse("rendiciones:rendicion_distribucion", args=[self.rendicion.pk]),
            data,
        )

    def test_guardar_distribucion_multiple(self):
        response = self._post_formset(
            [
                {"centro_costo": self.egc.pk, "monto": "200000", "descripcion": "EGC"},
                {"centro_costo": self.cga.pk, "monto": "100000", "descripcion": "CGA"},
            ]
        )
        self.assertEqual(response.status_code, 302)
        self.rendicion.refresh_from_db()
        self.assertEqual(self.rendicion.detalles.count(), 2)
        self.assertEqual(self.rendicion.total_distribuido, Decimal("300000.00"))
        self.assertTrue(self.rendicion.cuadra)
        self.assertEqual(self.rendicion.actualizado_por, self.user)

    def test_rechaza_monto_cero_en_formset(self):
        response = self._post_formset(
            [{"centro_costo": self.egc.pk, "monto": "0", "descripcion": "x"}]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.rendicion.detalles.count(), 0)
        self.assertContains(response, "mayor que cero")

    def test_detalle_muestra_lineas(self):
        agregar_detalle(
            self.rendicion,
            centro_costo=self.egc,
            monto="150000",
            descripcion="Materiales",
        )
        response = self.client.get(
            reverse("rendiciones:rendicion_detalle", args=[self.rendicion.pk])
        )
        self.assertContains(response, "EGC")
        self.assertContains(response, "Materiales")
        self.assertContains(response, "150")

    def test_no_edita_si_no_es_borrador(self):
        self.rendicion.estado = Rendicion.Estado.PRESENTADA
        self.rendicion.save(update_fields=["estado"])
        response = self.client.get(
            reverse("rendiciones:rendicion_distribucion", args=[self.rendicion.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.rendicion.detalles.count(), 0)
