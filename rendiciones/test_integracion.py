from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from rendiciones.models import Rendicion
from rendiciones.services.integracion import (
    datos_financieros,
    es_elegible_finanzas,
    estado_financiero,
    filas_excel,
)
from rendiciones.services.rendiciones import agregar_detalle
from rrhh.models import Trabajador

User = get_user_model()


class IntegracionServicioTests(TestCase):
    def setUp(self):
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.cga = CentroCosto.objects.create(codigo="CGA", nombre="CGA")
        self.ofi = CentroCosto.objects.create(codigo="OFI", nombre="Oficina")
        self.bodega = CentroCosto.objects.create(codigo="BODEGA", nombre="Bodega")

        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Compra de materiales",
            total_declarado=Decimal("385000.00"),
        )
        agregar_detalle(
            self.rendicion,
            centro_costo=self.egc,
            monto="200000",
            descripcion="EGC materiales",
        )
        agregar_detalle(self.rendicion, centro_costo=self.cga, monto="100000")
        agregar_detalle(self.rendicion, centro_costo=self.ofi, monto="85000")

    def _aprobar(self):
        self.rendicion.estado = Rendicion.Estado.APROBADA
        self.rendicion.save(update_fields=["estado"])

    def test_aprobada_elegible(self):
        self._aprobar()
        self.assertTrue(es_elegible_finanzas(self.rendicion))
        datos = datos_financieros(self.rendicion)
        self.assertEqual(len(datos["movimientos"]), 3)
        self.assertEqual(datos["total_movimientos"], Decimal("385000.00"))
        self.assertEqual(datos["total_declarado"], Decimal("385000.00"))
        codigos = [m["centro_costo_codigo"] for m in datos["movimientos"]]
        self.assertEqual(codigos, ["CGA", "EGC", "OFI"])
        self.assertTrue(all(m["tipo_movimiento"] == "EGRESO" for m in datos["movimientos"]))
        for m in datos["movimientos"]:
            self.assertTrue(m["clave"].startswith(f"REN-{self.rendicion.pk}-DET-"))
            self.assertEqual(m["estado"], Rendicion.Estado.APROBADA)

    def test_borrador_no_elegible(self):
        self.assertFalse(es_elegible_finanzas(self.rendicion))
        with self.assertRaises(ValidationError):
            datos_financieros(self.rendicion)

    def test_rechazada_no_elegible(self):
        self.rendicion.estado = Rendicion.Estado.RECHAZADA
        self.rendicion.save(update_fields=["estado"])
        with self.assertRaises(ValidationError):
            datos_financieros(self.rendicion)

    def test_distribucion_conserva_cc(self):
        self._aprobar()
        datos = datos_financieros(self.rendicion)
        egc = next(m for m in datos["movimientos"] if m["centro_costo_codigo"] == "EGC")
        self.assertEqual(egc["monto"], Decimal("200000.00"))
        self.assertEqual(egc["descripcion"], "EGC materiales")

    def test_total_salida_igual_total_rendicion(self):
        self._aprobar()
        datos = datos_financieros(self.rendicion)
        self.assertEqual(
            datos["total_movimientos"],
            datos["total_declarado"],
        )

    def test_filas_excel_matriz_dinamica_con_bodega(self):
        self._aprobar()
        otra = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 15),
            descripcion="Stock bodega",
            total_declarado=Decimal("10000.00"),
        )
        agregar_detalle(otra, centro_costo=self.bodega, monto="10000")
        otra.estado = Rendicion.Estado.APROBADA
        otra.save(update_fields=["estado"])

        qs = Rendicion.objects.filter(estado=Rendicion.Estado.APROBADA)
        filas = filas_excel(qs)
        encabezado = filas[0]
        self.assertIn("DESCRIPCION", encabezado)
        self.assertIn("EGC", encabezado)
        self.assertIn("BODEGA", encabezado)
        self.assertEqual(encabezado[-1], "TOTAL")
        # fila de materiales
        materiales = next(f for f in filas[1:] if f[3] == "Compra de materiales")
        idx_egc = encabezado.index("EGC")
        idx_bodega = encabezado.index("BODEGA")
        self.assertEqual(materiales[idx_egc], Decimal("200000.00"))
        self.assertEqual(materiales[idx_bodega], Decimal("0.00"))
        self.assertEqual(materiales[-1], Decimal("385000.00"))

    def test_estado_financiero_pendiente(self):
        self._aprobar()
        info = estado_financiero(self.rendicion)
        self.assertEqual(info["codigo"], "PENDIENTE")


class IntegracionFichaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("ren7", password="clave")
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Test",
            total_declarado=Decimal("1000"),
            estado=Rendicion.Estado.APROBADA,
        )
        # detalle directo para no pelear con puede_editar (ya APROBADA)
        from rendiciones.models import RendicionDetalle

        RendicionDetalle.objects.create(
            rendicion=self.rendicion,
            centro_costo=self.egc,
            monto=Decimal("1000"),
        )

    def test_ficha_muestra_estado_financiero(self):
        response = self.client.get(
            reverse("rendiciones:rendicion_detalle", args=[self.rendicion.pk])
        )
        self.assertContains(response, "Estado financiero")
        self.assertContains(response, "Pendiente de registrar")
