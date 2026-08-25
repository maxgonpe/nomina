from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from remuneraciones.models import (
    ConceptoCostoTrabajador,
    ConceptoRemuneracion,
    CostoTrabajadorPeriodo,
    HoraExtra,
    LiquidacionMensual,
)
from remuneraciones.services.costos import (
    generar_desde_liquidacion,
    generar_periodo,
    totales_por_centro,
)
from remuneraciones.services.liquidaciones import anular, calcular
from remuneraciones.services.movimientos import registrar_movimiento
from remuneraciones.services.periodos import (
    abrir,
    cerrar,
    crear,
    marcar_calculado,
    validar as validar_periodo,
)
from rrhh.models import AnexoContrato, Cargo, Contrato, Trabajador

User = get_user_model()


class Rem009Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_costotrabajadorperiodo",
                "change_costotrabajadorperiodo",
                "view_liquidacionmensual",
                "change_liquidacionmensual",
                "view_periodoremuneracion",
                "change_periodoremuneracion",
            ],
        )
        extra = Permission.objects.filter(
            content_type__app_label="rrhh",
            codename="view_trabajador",
        )
        self.user.user_permissions.set(list(perms) + list(extra))
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
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
        self.periodo = crear(anio=2026, mes=8, usuario=self.user)
        abrir(self.periodo, usuario=self.user)


class CostoMotorTests(Rem009Base):
    def test_catalogo_inicial(self):
        self.assertTrue(
            ConceptoCostoTrabajador.objects.filter(codigo="SUELDO_BASE").exists()
        )
        self.assertTrue(
            ConceptoCostoTrabajador.objects.filter(codigo="HHEX").exists()
        )
        total = ConceptoCostoTrabajador.objects.get(codigo="TOTAL_LIQUIDADO")
        self.assertFalse(total.incluye_en_total)
        self.assertEqual(total.codigo_origen, "")

    def test_calcular_liquidacion_genera_costo(self):
        HoraExtra.objects.create(
            trabajador=self.trabajador,
            periodo=self.periodo,
            fecha=date(2026, 8, 10),
            horas=Decimal("2.00"),
        )
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        costo = CostoTrabajadorPeriodo.objects.get(liquidacion=liq)
        self.assertEqual(costo.centro_costo_codigo_snapshot, "EGC")
        self.assertEqual(costo.dias_trabajados, Decimal("30.00"))
        self.assertEqual(
            costo.detalles.get(concepto__codigo="SUELDO_BASE").monto,
            Decimal("800000.00"),
        )
        self.assertEqual(
            costo.detalles.get(concepto__codigo="HHEX").monto,
            Decimal("12727.20"),
        )
        self.assertEqual(
            costo.detalles.get(concepto__codigo="TOTAL_LIQUIDADO").monto,
            liq.total_liquidado,
        )
        self.assertEqual(
            costo.total,
            sum(
                (
                    d.monto
                    for d in costo.detalles.select_related("concepto")
                    if d.concepto.incluye_en_total
                ),
                Decimal("0.00"),
            ),
        )
        # TOTAL_LIQUIDADO es referencia; no se suma dos veces al total
        self.assertEqual(
            costo.detalles.filter(concepto__incluye_en_total=False).count(),
            1,
        )

    def test_snapshot_cc_no_cambia_con_anexo_posterior(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        costo = generar_desde_liquidacion(liq, usuario=self.user)
        self.assertEqual(costo.centro_costo_codigo_snapshot, "EGC")
        AnexoContrato.objects.create(
            contrato=self.contrato,
            fecha_documento=date(2026, 9, 1),
            fecha_vigencia=date(2026, 9, 1),
            tipo=AnexoContrato.Tipo.CAMBIO_CENTRO_COSTO,
            nuevo_centro_costo=self.cc_ofi,
        )
        costo = generar_desde_liquidacion(liq, usuario=self.user)
        self.assertEqual(costo.centro_costo_codigo_snapshot, "EGC")
        self.assertEqual(costo.centro_costo_id, self.cc.pk)

    def test_bono_y_alojamiento_entran_al_costo(self):
        registrar_movimiento(
            trabajador=self.trabajador,
            periodo=self.periodo,
            concepto=ConceptoRemuneracion.objects.get(codigo="BONO_PRODUCCION"),
            monto=Decimal("50000"),
            usuario=self.user,
        )
        registrar_movimiento(
            trabajador=self.trabajador,
            periodo=self.periodo,
            concepto=ConceptoRemuneracion.objects.get(codigo="ALOJAMIENTO"),
            monto=Decimal("20000"),
            usuario=self.user,
        )
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        costo = liq.costo_trabajador
        self.assertEqual(
            costo.detalles.get(concepto__codigo="BONO_PRODUCCION").monto,
            Decimal("50000.00"),
        )
        self.assertEqual(
            costo.detalles.get(concepto__codigo="ALOJAMIENTO").monto,
            Decimal("20000.00"),
        )
        self.assertGreaterEqual(costo.total, Decimal("870000.00"))

    def test_concepto_costo_configurable(self):
        ConceptoCostoTrabajador.objects.create(
            codigo="BONO_FAENA",
            nombre="Bono faena (costo)",
            codigo_origen="BONO_FAENA",
            incluye_en_total=True,
            orden=75,
        )
        ConceptoRemuneracion.objects.get_or_create(
            codigo="BONO_FAENA",
            defaults={
                "nombre": "Bono faena",
                "tipo": ConceptoRemuneracion.Tipo.HABER,
                "naturaleza_calculo": ConceptoRemuneracion.NaturalezaCalculo.MANUAL,
                "editable": True,
                "orden": 85,
            },
        )
        registrar_movimiento(
            trabajador=self.trabajador,
            periodo=self.periodo,
            concepto=ConceptoRemuneracion.objects.get(codigo="BONO_FAENA"),
            monto=Decimal("15000"),
            usuario=self.user,
        )
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertEqual(
            liq.costo_trabajador.detalles.get(
                concepto__codigo="BONO_FAENA"
            ).monto,
            Decimal("15000.00"),
        )

    def test_anular_liquidacion_elimina_costo(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertTrue(
            CostoTrabajadorPeriodo.objects.filter(liquidacion=liq).exists()
        )
        anular(liq, usuario=self.user)
        self.assertFalse(
            CostoTrabajadorPeriodo.objects.filter(liquidacion=liq).exists()
        )

    def test_periodo_cerrado_no_regenera(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        marcar_calculado(self.periodo, usuario=self.user)
        validar_periodo(self.periodo, usuario=self.user)
        cerrar(self.periodo, usuario=self.user)
        with self.assertRaises(ValidationError):
            generar_desde_liquidacion(liq, usuario=self.user)

    def test_borrador_no_genera(self):
        liq = LiquidacionMensual.objects.create(
            periodo=self.periodo,
            trabajador=self.trabajador,
            contrato=self.contrato,
            estado=LiquidacionMensual.Estado.BORRADOR,
            centro_costo=self.cc,
        )
        with self.assertRaises(ValidationError):
            generar_desde_liquidacion(liq, usuario=self.user)

    def test_totales_por_centro(self):
        calcular(self.trabajador, self.periodo, usuario=self.user)
        filas = list(totales_por_centro(self.periodo))
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["centro_costo_codigo_snapshot"], "EGC")
        self.assertGreater(filas[0]["total"], 0)

    def test_generar_periodo(self):
        calcular(self.trabajador, self.periodo, usuario=self.user)
        ok, errores = generar_periodo(self.periodo, usuario=self.user)
        self.assertEqual(errores, [])
        self.assertEqual(len(ok), 1)


class CostoVistaTests(Rem009Base):
    def test_lista_y_detalle(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        costo = liq.costo_trabajador
        response = self.client.get(reverse("remuneraciones:costo_lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana Pérez")
        response = self.client.get(costo.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EGC")
        self.assertContains(response, "Sueldo base")

    def test_generar_desde_periodo_ui(self):
        calcular(self.trabajador, self.periodo, usuario=self.user)
        response = self.client.post(
            reverse("remuneraciones:periodo_generar_costos", args=[self.periodo.pk])
        )
        self.assertRedirects(
            response,
            reverse("remuneraciones:periodo_detalle", args=[self.periodo.pk]),
        )
        self.assertEqual(CostoTrabajadorPeriodo.objects.count(), 1)
