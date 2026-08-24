from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from remuneraciones.models import (
    Finiquito,
    HoraExtra,
    LiquidacionMensual,
    PeriodoRemuneracion,
)
from remuneraciones.services.periodos import (
    abrir,
    cerrar,
    crear,
    marcar_calculado,
    reabrir,
    validar,
)
from rrhh.models import Cargo, Contrato, Trabajador

User = get_user_model()


class Rem003Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_periodoremuneracion",
                "add_periodoremuneracion",
                "change_periodoremuneracion",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)

    def periodo_validado(self, anio=2026, mes=8):
        periodo = crear(anio=anio, mes=mes, usuario=self.user)
        abrir(periodo, usuario=self.user)
        marcar_calculado(periodo, usuario=self.user)
        validar(periodo, usuario=self.user)
        return periodo

    def trabajador_con_contrato(self):
        trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        cargo = Cargo.objects.create(codigo="MAESTRO", nombre="Maestro")
        cc = CentroCosto.objects.create(
            codigo="EGC",
            nombre="Edificio Gran Costanera",
            tipo=CentroCosto.Tipo.OBRA,
        )
        contrato = Contrato.objects.create(
            trabajador=trabajador,
            cargo=cargo,
            centro_costo=cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        return trabajador, contrato


class PeriodoIndependienteExcelTests(Rem003Base):
    def test_fechas_se_derivan_del_mes(self):
        periodo = crear(anio=2026, mes=8, usuario=self.user)
        self.assertEqual(periodo.fecha_inicio, date(2026, 8, 1))
        self.assertEqual(periodo.fecha_fin, date(2026, 8, 31))
        self.assertEqual(periodo.estado, PeriodoRemuneracion.Estado.BORRADOR)
        self.assertEqual(periodo.nombre_hoja_excel, "AGOSTO")

    def test_febrero_bisiesto(self):
        periodo = crear(anio=2028, mes=2)
        self.assertEqual(periodo.fecha_fin, date(2028, 2, 29))

    def test_puede_existir_agosto_sin_septiembre(self):
        crear(anio=2026, mes=8)
        self.assertFalse(
            PeriodoRemuneracion.objects.filter(anio=2026, mes=9).exists()
        )
        self.assertEqual(PeriodoRemuneracion.objects.count(), 1)

    def test_rechaza_mes_duplicado(self):
        crear(anio=2026, mes=8)
        with self.assertRaises(ValidationError):
            crear(anio=2026, mes=8)

    def test_rechaza_mes_fuera_de_rango(self):
        periodo = PeriodoRemuneracion(anio=2026, mes=13)
        with self.assertRaises(ValidationError):
            periodo.full_clean()


class FlujoEstadosTests(Rem003Base):
    def test_flujo_hasta_cerrado(self):
        periodo = self.periodo_validado()
        cerrado = cerrar(periodo, usuario=self.user)
        self.assertEqual(cerrado.estado, PeriodoRemuneracion.Estado.CERRADO)
        self.assertIsNotNone(cerrado.cerrado_en)
        self.assertEqual(cerrado.cerrado_por, self.user)

    def test_no_salta_estados(self):
        periodo = crear(anio=2026, mes=1)
        with self.assertRaises(ValidationError):
            marcar_calculado(periodo)
        with self.assertRaises(ValidationError):
            cerrar(periodo, usuario=self.user)

    def test_no_cierra_con_liquidacion_borrador(self):
        periodo = self.periodo_validado()
        trabajador, contrato = self.trabajador_con_contrato()
        LiquidacionMensual.objects.create(
            periodo=periodo,
            trabajador=trabajador,
            contrato=contrato,
            estado=LiquidacionMensual.Estado.BORRADOR,
        )
        with self.assertRaises(ValidationError):
            cerrar(periodo, usuario=self.user)

    def test_no_cierra_sin_recalcular(self):
        periodo = self.periodo_validado()
        trabajador, contrato = self.trabajador_con_contrato()
        LiquidacionMensual.objects.create(
            periodo=periodo,
            trabajador=trabajador,
            contrato=contrato,
            estado=LiquidacionMensual.Estado.CALCULADA,
            requiere_recalculo=True,
        )
        with self.assertRaises(ValidationError):
            cerrar(periodo, usuario=self.user)


class CierreBloqueaCambiosTests(Rem003Base):
    def setUp(self):
        super().setUp()
        self.periodo = self.periodo_validado()
        cerrar(self.periodo, usuario=self.user)
        self.periodo.refresh_from_db()
        self.trabajador, self.contrato = self.trabajador_con_contrato()

    def test_no_agrega_hora_extra(self):
        with self.assertRaises(ValidationError):
            HoraExtra.objects.create(
                trabajador=self.trabajador,
                periodo=self.periodo,
                fecha=date(2026, 8, 10),
                horas=Decimal("2.00"),
            )

    def test_no_agrega_liquidacion_ni_movimiento(self):
        with self.assertRaises(ValidationError):
            LiquidacionMensual.objects.create(
                periodo=self.periodo,
                trabajador=self.trabajador,
                contrato=self.contrato,
                estado=LiquidacionMensual.Estado.CALCULADA,
                requiere_recalculo=False,
            )

    def test_no_modifica_finiquito(self):
        with self.assertRaises(ValidationError):
            Finiquito.objects.create(
                trabajador=self.trabajador,
                contrato=self.contrato,
                periodo=self.periodo,
                fecha=date(2026, 8, 31),
                monto=Decimal("100000"),
            )

    def test_reapertura_exige_motivo_y_permite_editar(self):
        with self.assertRaises(ValidationError):
            reabrir(self.periodo, motivo="   ")
        reabrir(
            self.periodo,
            motivo="Corrección de horas extra de obra EGC.",
            usuario=self.user,
        )
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, PeriodoRemuneracion.Estado.ABIERTO)
        self.assertIn("horas extra", self.periodo.motivo_reapertura)
        he = HoraExtra.objects.create(
            trabajador=self.trabajador,
            periodo=self.periodo,
            fecha=date(2026, 8, 10),
            horas=Decimal("2.00"),
        )
        self.assertEqual(he.horas, Decimal("2.00"))


class PeriodoVistaTests(Rem003Base):
    def test_lista_y_alta(self):
        response = self.client.get(reverse("remuneraciones:periodo_lista"))
        self.assertEqual(response.status_code, 200)
        crear_url = reverse("remuneraciones:periodo_crear")
        response = self.client.post(
            crear_url,
            {"anio": "2026", "mes": "8", "observaciones": "Agosto real"},
        )
        self.assertEqual(PeriodoRemuneracion.objects.count(), 1)
        periodo = PeriodoRemuneracion.objects.get()
        self.assertRedirects(
            response,
            reverse("remuneraciones:periodo_detalle", args=[periodo.pk]),
        )
        self.assertEqual(periodo.estado, PeriodoRemuneracion.Estado.BORRADOR)

    def test_abrir_y_cerrar_desde_ui(self):
        periodo = crear(anio=2026, mes=7, usuario=self.user)
        self.client.post(
            reverse("remuneraciones:periodo_abrir", args=[periodo.pk])
        )
        periodo.refresh_from_db()
        self.assertEqual(periodo.estado, PeriodoRemuneracion.Estado.ABIERTO)
        self.client.post(
            reverse("remuneraciones:periodo_calcular", args=[periodo.pk])
        )
        self.client.post(
            reverse("remuneraciones:periodo_validar", args=[periodo.pk])
        )
        response = self.client.post(
            reverse("remuneraciones:periodo_cerrar", args=[periodo.pk])
        )
        periodo.refresh_from_db()
        self.assertEqual(periodo.estado, PeriodoRemuneracion.Estado.CERRADO)
        self.assertRedirects(
            response,
            reverse("remuneraciones:periodo_detalle", args=[periodo.pk]),
        )

    def test_reabrir_desde_ui_con_motivo(self):
        periodo = self.periodo_validado(mes=3)
        cerrar(periodo, usuario=self.user)
        response = self.client.post(
            reverse("remuneraciones:periodo_reabrir", args=[periodo.pk]),
            {"motivo": "Ajuste de anticipo informado fuera de plazo."},
        )
        periodo.refresh_from_db()
        self.assertEqual(periodo.estado, PeriodoRemuneracion.Estado.ABIERTO)
        self.assertRedirects(
            response,
            reverse("remuneraciones:periodo_detalle", args=[periodo.pk]),
        )
