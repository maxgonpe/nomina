from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from rendiciones.models import Rendicion
from rendiciones.services.rendiciones import agregar_detalle
from rendiciones.services.reportes import (
    ESTADOS_OFICIALES,
    filas_exportacion,
    filtrar_rendiciones,
    resumen_por_centro,
)
from rrhh.models import Trabajador

User = get_user_model()


class ReportesServicioTests(TestCase):
    def setUp(self):
        self.ana = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.bruno = Trabajador.objects.create(
            rut="11.111.111-1",
            nombre_completo="Bruno Soto",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.cga = CentroCosto.objects.create(codigo="CGA", nombre="CGA")
        self.ofi = CentroCosto.objects.create(codigo="OFI", nombre="Oficina")

        self.r1 = Rendicion.objects.create(
            trabajador=self.ana,
            fecha=date(2026, 8, 12),
            descripcion="Materiales",
            total_declarado=Decimal("300000.00"),
        )
        agregar_detalle(self.r1, centro_costo=self.egc, monto="200000")
        agregar_detalle(self.r1, centro_costo=self.cga, monto="100000")
        self.r1.estado = Rendicion.Estado.APROBADA
        self.r1.save(update_fields=["estado"])

        self.r2 = Rendicion.objects.create(
            trabajador=self.bruno,
            fecha=date(2026, 8, 20),
            descripcion="Oficina",
            total_declarado=Decimal("50000.00"),
        )
        agregar_detalle(self.r2, centro_costo=self.ofi, monto="50000")
        self.r2.estado = Rendicion.Estado.PAGADA
        self.r2.save(update_fields=["estado"])

        self.r3 = Rendicion.objects.create(
            trabajador=self.ana,
            fecha=date(2026, 7, 5),
            descripcion="Borrador julio",
            total_declarado=Decimal("10000.00"),
        )
        agregar_detalle(self.r3, centro_costo=self.egc, monto="10000")

        self.r4 = Rendicion.objects.create(
            trabajador=self.ana,
            fecha=date(2025, 8, 1),
            descripcion="Año anterior",
            total_declarado=Decimal("9000.00"),
        )
        agregar_detalle(self.r4, centro_costo=self.egc, monto="9000")
        self.r4.estado = Rendicion.Estado.APROBADA
        self.r4.save(update_fields=["estado"])

    def test_filtro_anio(self):
        qs = filtrar_rendiciones(anio=2026)
        self.assertEqual(qs.count(), 3)

    def test_filtro_mes(self):
        qs = filtrar_rendiciones(anio=2026, mes=8)
        self.assertEqual(qs.count(), 2)

    def test_filtro_trabajador(self):
        qs = filtrar_rendiciones(trabajador_id=self.bruno.pk)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.get().descripcion, "Oficina")

    def test_filtro_centro(self):
        qs = filtrar_rendiciones(centro_costo_id=self.ofi.pk)
        self.assertEqual(qs.count(), 1)

    def test_filtro_estado(self):
        qs = filtrar_rendiciones(estados=[Rendicion.Estado.PAGADA])
        self.assertEqual(qs.count(), 1)

    def test_totales_por_centro_oficiales(self):
        resumen = resumen_por_centro(anio=2026, mes=8)
        self.assertEqual(set(resumen["estados"]), set(ESTADOS_OFICIALES))
        por_codigo = {f["codigo"]: f["total"] for f in resumen["por_centro"]}
        self.assertEqual(por_codigo["EGC"], Decimal("200000.00"))
        self.assertEqual(por_codigo["CGA"], Decimal("100000.00"))
        self.assertEqual(por_codigo["OFI"], Decimal("50000.00"))
        self.assertEqual(resumen["total_distribuido"], Decimal("350000.00"))
        self.assertEqual(resumen["cantidad_rendiciones"], 2)

    def test_totales_globales_y_exportacion(self):
        resumen = resumen_por_centro(anio=2026, mes=8)
        filas = filas_exportacion(resumen)
        self.assertEqual(filas[0], ["CENTRO", "NOMBRE", "TOTAL"])
        self.assertEqual(filas[-1][0], "TOTAL")
        self.assertEqual(filas[-1][-1], Decimal("350000.00"))


class ReportesVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ren6", password="clave")
        perms = Permission.objects.filter(
            content_type__app_label="rendiciones",
            codename="view_rendicion",
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        r = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Materiales",
            total_declarado=Decimal("100000"),
        )
        agregar_detalle(r, centro_costo=self.egc, monto="100000")
        r.estado = Rendicion.Estado.APROBADA
        r.save(update_fields=["estado"])

    def test_listado_filtra_anio_mes(self):
        response = self.client.get(
            reverse("rendiciones:rendicion_lista"),
            {"anio": "2026", "mes": "8"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Materiales")

    def test_resumen_muestra_centros(self):
        response = self.client.get(
            reverse("rendiciones:rendicion_resumen"),
            {"anio": "2026", "mes": "8"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EGC")
        self.assertContains(response, "Aprobada")
        self.assertContains(response, "Pagada")
