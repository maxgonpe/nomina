from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from remuneraciones.models import HoraExtra, LiquidacionMensual, PeriodoRemuneracion
from remuneraciones.services.horas_extra import suma_horas_extra
from remuneraciones.services.periodos import (
    abrir,
    cerrar,
    crear,
    marcar_calculado,
    validar,
)
from rrhh.models import Cargo, Contrato, Trabajador

User = get_user_model()


class Rem006Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_horaextra",
                "add_horaextra",
                "change_horaextra",
                "delete_horaextra",
                "view_periodoremuneracion",
                "change_periodoremuneracion",
                "view_trabajador",
            ],
        )
        # view_trabajador is in rrhh
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
        self.contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            centro_costo=self.cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        self.periodo = crear(anio=2026, mes=8, usuario=self.user)
        abrir(self.periodo, usuario=self.user)

    def _he(self, horas, dia=10, **kwargs):
        return HoraExtra.objects.create(
            trabajador=self.trabajador,
            periodo=self.periodo,
            fecha=date(2026, 8, dia),
            horas=Decimal(str(horas)),
            **kwargs,
        )


class SumaHorasExtraTests(Rem006Base):
    def test_suma_es_el_insumo_de_rem005(self):
        self._he("2.00", dia=3, actividad="Obra EGC")
        self._he("3.50", dia=12, actividad="Oficina")
        self.assertEqual(
            suma_horas_extra(self.trabajador, self.periodo),
            Decimal("5.50"),
        )

    def test_fecha_fuera_del_periodo(self):
        he = HoraExtra(
            trabajador=self.trabajador,
            periodo=self.periodo,
            fecha=date(2026, 7, 31),
            horas=Decimal("1.00"),
        )
        with self.assertRaises(ValidationError):
            he.full_clean()

    def test_horas_deben_ser_positivas(self):
        he = HoraExtra(
            trabajador=self.trabajador,
            periodo=self.periodo,
            fecha=date(2026, 8, 1),
            horas=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            he.full_clean()

    def test_modificar_marca_liquidacion_pendiente(self):
        liq = LiquidacionMensual.objects.create(
            periodo=self.periodo,
            trabajador=self.trabajador,
            contrato=self.contrato,
            estado=LiquidacionMensual.Estado.CALCULADA,
            requiere_recalculo=False,
        )
        self._he("2.00")
        liq.refresh_from_db()
        self.assertTrue(liq.requiere_recalculo)

    def test_cerrado_no_crea_ni_borra(self):
        he = self._he("1.00")
        marcar_calculado(self.periodo, usuario=self.user)
        validar(self.periodo, usuario=self.user)
        # La liquidación quedó con recálculo; anularla para poder cerrar.
        LiquidacionMensual.objects.filter(periodo=self.periodo).update(
            estado=LiquidacionMensual.Estado.ANULADA,
            requiere_recalculo=False,
        )
        cerrar(self.periodo, usuario=self.user)
        self.periodo.refresh_from_db()
        with self.assertRaises(ValidationError):
            HoraExtra.objects.create(
                trabajador=self.trabajador,
                periodo=self.periodo,
                fecha=date(2026, 8, 20),
                horas=Decimal("1.00"),
            )
        he = HoraExtra.objects.get(pk=he.pk)
        with self.assertRaises(ValidationError):
            he.delete()


class HoraExtraVistaTests(Rem006Base):
    def test_lista_y_alta(self):
        response = self.client.get(reverse("remuneraciones:hora_extra_lista"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("remuneraciones:hora_extra_crear"),
            {
                "trabajador": self.trabajador.pk,
                "periodo": self.periodo.pk,
                "fecha": "2026-08-05",
                "horas": "2.25",
                "actividad": "Traslado",
            },
        )
        self.assertEqual(HoraExtra.objects.count(), 1)
        self.assertEqual(
            suma_horas_extra(self.trabajador, self.periodo),
            Decimal("2.25"),
        )

    def test_carga_rapida_en_periodo_sin_salir(self):
        url = reverse(
            "remuneraciones:periodo_horas_extra",
            args=[self.periodo.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            url,
            {
                "he-TOTAL_FORMS": "3",
                "he-INITIAL_FORMS": "0",
                "he-MIN_NUM_FORMS": "0",
                "he-MAX_NUM_FORMS": "1000",
                "he-0-trabajador": str(self.trabajador.pk),
                "he-0-fecha": "2026-08-10",
                "he-0-horas": "2",
                "he-0-actividad": "Obra",
                "he-1-trabajador": str(self.trabajador.pk),
                "he-1-fecha": "2026-08-11",
                "he-1-horas": "1.5",
                "he-1-actividad": "Oficina",
                "he-2-trabajador": "",
                "he-2-fecha": "",
                "he-2-horas": "",
                "he-2-actividad": "",
            },
        )
        self.assertRedirects(response, url)
        self.assertEqual(HoraExtra.objects.count(), 2)
        self.assertEqual(
            suma_horas_extra(self.trabajador, self.periodo),
            Decimal("3.50"),
        )
