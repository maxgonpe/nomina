from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from remuneraciones.models import LiquidacionMensual, PagoRemuneracion
from remuneraciones.services.liquidaciones import calcular
from remuneraciones.services.periodos import abrir, crear
from remuneraciones.services.resumenes import (
    METRICA_A_PAGAR,
    METRICA_PAGADO,
    filas_exportacion,
    resumen_anual,
)
from rrhh.models import Cargo, Contrato, Trabajador

User = get_user_model()


class Rem010Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_liquidacionmensual",
                "change_liquidacionmensual",
                "view_periodoremuneracion",
                "change_periodoremuneracion",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.otro = Trabajador.objects.create(
            rut="11.111.111-1",
            nombre_completo="Bruno Soto",
        )
        self.cargo = Cargo.objects.create(codigo="MAESTRO", nombre="Maestro")
        self.cc = CentroCosto.objects.create(
            codigo="EGC",
            nombre="Edificio Gran Costanera",
            tipo=CentroCosto.Tipo.OBRA,
        )
        self.cc_ofi = CentroCosto.objects.create(
            codigo="OFI",
            nombre="Oficina Central",
            tipo=CentroCosto.Tipo.ADMINISTRATIVO,
        )
        self.contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            centro_costo=self.cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        Contrato.objects.create(
            trabajador=self.otro,
            cargo=self.cargo,
            centro_costo=self.cc_ofi,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("500000"),
        )

    def _periodo(self, mes):
        periodo = crear(anio=2026, mes=mes, usuario=self.user)
        abrir(periodo, usuario=self.user)
        return periodo


class ResumenAnualServiceTests(Rem010Base):
    def test_no_hay_modelo_resumen_por_anio(self):
        from django.apps import apps

        nombres = {m.__name__ for m in apps.get_models()}
        self.assertNotIn("Resumen2026", nombres)
        self.assertNotIn("ResumenAnual", nombres)
        campos = {f.name for f in LiquidacionMensual._meta.get_fields()}
        self.assertNotIn("enero", campos)
        self.assertNotIn("febrero", campos)

    def test_meses_sin_liquidacion_quedan_en_cero(self):
        ene = self._periodo(1)
        calcular(self.trabajador, ene, usuario=self.user)
        resumen = resumen_anual(2026, metrica=METRICA_A_PAGAR)
        self.assertEqual(len(resumen["filas"]), 1)
        fila = resumen["filas"][0]
        self.assertEqual(fila["valores_mes"][0], Decimal("800000.00"))
        self.assertEqual(fila["valores_mes"][2], Decimal("0.00"))  # marzo
        self.assertEqual(fila["total"], Decimal("800000.00"))
        self.assertEqual(resumen["totales_mes"][0], Decimal("800000.00"))
        self.assertEqual(resumen["totales_mes"][2], Decimal("0.00"))
        self.assertEqual(resumen["total_anual"], Decimal("800000.00"))
        self.assertEqual(resumen["grafico"]["labels"][0], "ENERO")
        self.assertEqual(resumen["grafico"]["valores"][0], 800000.0)

    def test_varios_meses_y_trabajadores(self):
        calcular(self.trabajador, self._periodo(1), usuario=self.user)
        ago = self._periodo(8)
        calcular(self.trabajador, ago, usuario=self.user)
        calcular(self.otro, ago, usuario=self.user)
        resumen = resumen_anual(2026)
        self.assertEqual(len(resumen["filas"]), 2)
        ana = next(f for f in resumen["filas"] if f["nombre"] == "Ana Pérez")
        self.assertEqual(ana["total"], Decimal("1600000.00"))
        self.assertEqual(resumen["totales_mes"][7], Decimal("1300000.00"))
        self.assertEqual(resumen["total_anual"], Decimal("2100000.00"))

    def test_metrica_pagado_distinta_de_a_pagar(self):
        liq = calcular(self.trabajador, self._periodo(8), usuario=self.user)
        PagoRemuneracion.objects.create(
            liquidacion=liq,
            fecha=date(2026, 8, 28),
            monto=Decimal("100000"),
            medio_pago=PagoRemuneracion.MedioPago.TRANSFERENCIA,
        )
        a_pagar = resumen_anual(2026, metrica=METRICA_A_PAGAR)
        pagado = resumen_anual(2026, metrica=METRICA_PAGADO)
        self.assertEqual(a_pagar["metrica_label"], "Total a pagar")
        self.assertEqual(pagado["metrica_label"], "Total pagado")
        self.assertEqual(a_pagar["total_anual"], Decimal("800000.00"))
        self.assertEqual(pagado["total_anual"], Decimal("100000.00"))
        self.assertNotEqual(a_pagar["total_anual"], pagado["total_anual"])

    def test_filtro_trabajador_y_centro(self):
        ago = self._periodo(8)
        calcular(self.trabajador, ago, usuario=self.user)
        calcular(self.otro, ago, usuario=self.user)
        solo_ana = resumen_anual(
            2026, trabajador_id=self.trabajador.pk
        )
        self.assertEqual(len(solo_ana["filas"]), 1)
        self.assertEqual(solo_ana["filas"][0]["nombre"], "Ana Pérez")
        por_ofi = resumen_anual(2026, centro_costo_id=self.cc_ofi.pk)
        self.assertEqual(len(por_ofi["filas"]), 1)
        self.assertEqual(por_ofi["filas"][0]["nombre"], "Bruno Soto")

    def test_exportacion_preparada(self):
        calcular(self.trabajador, self._periodo(1), usuario=self.user)
        filas = filas_exportacion(resumen_anual(2026))
        self.assertEqual(filas[0][0], "NOMBRE")
        self.assertEqual(filas[0][3], "ENERO")
        self.assertEqual(filas[0][-1], "TOTAL")
        self.assertEqual(filas[1][0], "Ana Pérez")
        self.assertEqual(filas[-1][0], "TOTAL")

    def test_anio_sin_datos(self):
        resumen = resumen_anual(2099)
        self.assertEqual(resumen["filas"], [])
        self.assertEqual(resumen["total_anual"], Decimal("0.00"))
        self.assertEqual(len(resumen["grafico"]["valores"]), 12)


class ResumenAnualVistaTests(Rem010Base):
    def test_vista_resumen(self):
        calcular(self.trabajador, self._periodo(8), usuario=self.user)
        response = self.client.get(
            reverse("remuneraciones:resumen_anual", args=[2026])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumen anual 2026")
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Total a pagar")
        self.assertContains(response, "grafico-resumen-anual")
        self.assertContains(response, "resumen-grafico-data")

    def test_redirect_anio_actual(self):
        response = self.client.get(
            reverse("remuneraciones:resumen_anual_actual")
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/remuneraciones/resumen/", response.url)

    def test_filtro_metrica_en_url(self):
        liq = calcular(self.trabajador, self._periodo(8), usuario=self.user)
        PagoRemuneracion.objects.create(
            liquidacion=liq,
            fecha=date(2026, 8, 28),
            monto=Decimal("50000"),
            medio_pago=PagoRemuneracion.MedioPago.EFECTIVO,
        )
        response = self.client.get(
            reverse("remuneraciones:resumen_anual", args=[2026]),
            {"metrica": "pagado"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total pagado")
