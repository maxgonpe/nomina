from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto
from rrhh.models import AnexoContrato, Cargo, Contrato, Trabajador
from rrhh.services.contratos import condicion_vigente

User = get_user_model()


class Rem002Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="rrhh",
            codename__in=[
                "view_trabajador",
                "view_cargo",
                "add_cargo",
                "change_cargo",
                "view_contrato",
                "add_contrato",
                "change_contrato",
                "view_anexocontrato",
                "add_anexocontrato",
                "change_anexocontrato",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.cargo = Cargo.objects.create(
            codigo="MAESTRO",
            nombre="Maestro",
        )
        self.cargo_sup = Cargo.objects.create(
            codigo="SUPERVISOR",
            nombre="Supervisor",
        )
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


class CondicionVigenteTests(Rem002Base):
    def test_sueldo_cargo_y_cc_segun_fecha(self):
        contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            centro_costo=self.cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        AnexoContrato.objects.create(
            contrato=contrato,
            fecha_documento=date(2026, 4, 20),
            fecha_vigencia=date(2026, 5, 1),
            tipo=AnexoContrato.Tipo.CAMBIO_SUELDO,
            nuevo_sueldo_base=Decimal("900000"),
        )
        AnexoContrato.objects.create(
            contrato=contrato,
            fecha_documento=date(2026, 6, 1),
            fecha_vigencia=date(2026, 7, 1),
            tipo=AnexoContrato.Tipo.CAMBIO_CARGO,
            nuevo_cargo=self.cargo_sup,
        )
        AnexoContrato.objects.create(
            contrato=contrato,
            fecha_documento=date(2026, 6, 1),
            fecha_vigencia=date(2026, 7, 1),
            tipo=AnexoContrato.Tipo.CAMBIO_CENTRO_COSTO,
            nuevo_centro_costo=self.cc_ofi,
        )

        ene = condicion_vigente(self.trabajador, date(2026, 1, 15))
        self.assertEqual(ene.sueldo_base, Decimal("800000"))
        self.assertEqual(ene.cargo, self.cargo)
        self.assertEqual(ene.centro_costo, self.cc)

        abr = condicion_vigente(self.trabajador, date(2026, 4, 30))
        self.assertEqual(abr.sueldo_base, Decimal("800000"))

        may = condicion_vigente(self.trabajador, date(2026, 5, 1))
        self.assertEqual(may.sueldo_base, Decimal("900000"))
        self.assertEqual(may.cargo, self.cargo)

        ago = condicion_vigente(self.trabajador, date(2026, 8, 1))
        self.assertEqual(ago.sueldo_base, Decimal("900000"))
        self.assertEqual(ago.cargo, self.cargo_sup)
        self.assertEqual(ago.centro_costo, self.cc_ofi)

    def test_sin_contrato_en_fecha(self):
        self.assertIsNone(
            condicion_vigente(self.trabajador, date(2025, 12, 1))
        )


class ContratoValidacionTests(Rem002Base):
    def test_rechaza_sueldo_cero(self):
        c = Contrato(
            trabajador=self.trabajador,
            cargo=self.cargo,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("0"),
        )
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_rechaza_termino_anterior_al_inicio(self):
        c = Contrato(
            trabajador=self.trabajador,
            cargo=self.cargo,
            fecha_inicio=date(2026, 3, 1),
            fecha_termino=date(2026, 2, 1),
            sueldo_base_inicial=Decimal("500000"),
        )
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_rechaza_contratos_solapados(self):
        Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        otro = Contrato(
            trabajador=self.trabajador,
            cargo=self.cargo,
            fecha_inicio=date(2026, 6, 1),
            sueldo_base_inicial=Decimal("900000"),
        )
        with self.assertRaises(ValidationError):
            otro.full_clean()

    def test_anexo_antes_del_contrato(self):
        contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            fecha_inicio=date(2026, 3, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        anexo = AnexoContrato(
            contrato=contrato,
            fecha_documento=date(2026, 1, 1),
            fecha_vigencia=date(2026, 2, 1),
            tipo=AnexoContrato.Tipo.CAMBIO_SUELDO,
            nuevo_sueldo_base=Decimal("900000"),
        )
        with self.assertRaises(ValidationError):
            anexo.full_clean()


class Rem002VistaTests(Rem002Base):
    def test_crea_cargo(self):
        response = self.client.post(
            reverse("rrhh:cargo_crear"),
            {
                "codigo": "ayudante",
                "nombre": "Ayudante",
                "descripcion": "",
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Cargo.objects.filter(codigo="AYUDANTE", nombre="Ayudante").exists()
        )

    def test_crea_contrato_desde_trabajador(self):
        url = reverse(
            "rrhh:trabajador_contrato_crear",
            args=[self.trabajador.pk],
        )
        response = self.client.post(
            url,
            {
                "trabajador": self.trabajador.pk,
                "cargo": self.cargo.pk,
                "centro_costo": self.cc.pk,
                "tipo_contrato": Contrato.TipoContrato.INDEFINIDO,
                "fecha_inicio": "2026-01-01",
                "sueldo_base_inicial": "800000",
                "estado": Contrato.Estado.VIGENTE,
            },
        )
        self.assertEqual(response.status_code, 302)
        contrato = Contrato.objects.get()
        self.assertEqual(contrato.trabajador, self.trabajador)
        self.assertEqual(contrato.sueldo_base_inicial, Decimal("800000"))

    def test_crea_anexo_y_se_refleja_en_detalle(self):
        contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            centro_costo=self.cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        url = reverse("rrhh:anexo_crear", args=[contrato.pk])
        response = self.client.post(
            url,
            {
                "fecha_documento": "2026-04-20",
                "fecha_vigencia": "2026-05-01",
                "tipo": AnexoContrato.Tipo.CAMBIO_SUELDO,
                "nuevo_sueldo_base": "900000",
                "descripcion": "Reajuste",
            },
        )
        self.assertEqual(response.status_code, 302)
        detalle = self.client.get(
            reverse("rrhh:trabajador_detalle", args=[self.trabajador.pk])
            + "?fecha=2026-08-01"
        )
        self.assertContains(detalle, "Cambio de sueldo")
        self.assertContains(detalle, "Maestro")
