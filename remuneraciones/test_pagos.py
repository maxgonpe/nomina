from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CentroCosto
from remuneraciones.models import LiquidacionMensual, PagoRemuneracion
from remuneraciones.services.liquidaciones import (
    calcular,
    marcar_pagada,
    validar,
)
from remuneraciones.services.pagos import anular_pago, registrar_pago
from remuneraciones.services.periodos import abrir, crear
from remuneraciones.services.resumenes import METRICA_PAGADO, resumen_anual
from rrhh.models import Cargo, Contrato, Trabajador

User = get_user_model()


class Rem005C01Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_liquidacionmensual",
                "change_liquidacionmensual",
                "add_pagoremuneracion",
                "anular_pagoremuneracion",
                "view_periodoremuneracion",
            ],
        )
        self.user.user_permissions.set(perms)
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

    def _liquidacion_validada(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        validar(liq, usuario=self.user)
        liq.refresh_from_db()
        return liq


class PagoRegistroTests(Rem005C01Base):
    def test_registrar_pago_total(self):
        liq = self._liquidacion_validada()
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        self.assertEqual(liq.total_pagado, Decimal("800000.00"))
        self.assertEqual(liq.saldo_pendiente, Decimal("0.00"))
        self.assertEqual(liq.estado_pago, "PAGADA")

    def test_registrar_pago_parcial(self):
        liq = self._liquidacion_validada()
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("300000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        self.assertEqual(liq.total_pagado, Decimal("300000.00"))
        self.assertEqual(liq.saldo_pendiente, Decimal("500000.00"))
        self.assertEqual(liq.estado_pago, "PAGO PARCIAL")

    def test_rechazar_pago_cero(self):
        liq = self._liquidacion_validada()
        with self.assertRaises(ValidationError):
            registrar_pago(
                liq,
                fecha=timezone.localdate(),
                monto=Decimal("0"),
                usuario=self.user,
            )

    def test_rechazar_sobrepago(self):
        liq = self._liquidacion_validada()
        with self.assertRaises(ValidationError) as ctx:
            registrar_pago(
                liq,
                fecha=timezone.localdate(),
                monto=Decimal("800001"),
                usuario=self.user,
            )
        self.assertIn("excede el saldo pendiente", str(ctx.exception))
        self.assertEqual(liq.pagos.count(), 0)

    def test_multiples_pagos_parciales(self):
        liq = self._liquidacion_validada()
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("300000"),
            usuario=self.user,
        )
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("200000"),
            usuario=self.user,
        )
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("300000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        self.assertEqual(liq.total_pagado, Decimal("800000.00"))
        self.assertEqual(liq.saldo_pendiente, Decimal("0.00"))


class PagoEstadoTests(Rem005C01Base):
    def test_pago_parcial_no_marca_pagada(self):
        liq = self._liquidacion_validada()
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("100000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        with self.assertRaises(ValidationError):
            marcar_pagada(liq, usuario=self.user)

    def test_pago_total_marca_pagada(self):
        liq = self._liquidacion_validada()
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        marcar_pagada(liq, usuario=self.user)
        liq.refresh_from_db()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.PAGADA)


class PagoAnulacionTests(Rem005C01Base):
    def test_anular_pago(self):
        liq = self._liquidacion_validada()
        pago = registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        anular_pago(
            pago,
            motivo="Error de digitación",
            usuario=self.user,
        )
        pago.refresh_from_db()
        self.assertTrue(pago.anulado)
        self.assertEqual(pago.motivo_anulacion, "Error de digitación")
        self.assertEqual(pago.anulado_por, self.user)

    def test_anulacion_requiere_motivo(self):
        liq = self._liquidacion_validada()
        pago = registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("100000"),
            usuario=self.user,
        )
        with self.assertRaises(ValidationError):
            anular_pago(pago, motivo="", usuario=self.user)

    def test_no_anular_dos_veces(self):
        liq = self._liquidacion_validada()
        pago = registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("100000"),
            usuario=self.user,
        )
        anular_pago(pago, motivo="Error", usuario=self.user)
        with self.assertRaises(ValidationError):
            anular_pago(pago, motivo="Otra vez", usuario=self.user)

    def test_pago_anulado_no_suma_total_pagado(self):
        liq = self._liquidacion_validada()
        pago = registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        anular_pago(pago, motivo="Error de digitación", usuario=self.user)
        liq.refresh_from_db()
        self.assertEqual(liq.total_pagado, Decimal("0.00"))
        self.assertEqual(liq.saldo_pendiente, Decimal("800000.00"))

    def test_anular_pago_revierte_estado_pagada(self):
        liq = self._liquidacion_validada()
        pago = registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        marcar_pagada(liq, usuario=self.user)
        liq.refresh_from_db()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.PAGADA)
        anular_pago(pago, motivo="Error de digitación", usuario=self.user)
        liq.refresh_from_db()
        self.assertEqual(liq.total_pagado, Decimal("0.00"))
        self.assertEqual(liq.saldo_pendiente, Decimal("800000.00"))
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.VALIDADA)

    def test_corregir_pago_tras_anulacion(self):
        liq = self._liquidacion_validada()
        incorrecto = registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        anular_pago(
            incorrecto,
            motivo="Error de digitación",
            usuario=self.user,
        )
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        self.assertEqual(liq.pagos.filter(anulado=True).count(), 1)
        self.assertEqual(liq.pagos.filter(anulado=False).count(), 1)
        self.assertEqual(liq.total_pagado, Decimal("800000.00"))


class PagoVistaTests(Rem005C01Base):
    def test_rechazar_sobrepago_desde_ui(self):
        liq = self._liquidacion_validada()
        response = self.client.post(
            reverse("remuneraciones:liquidacion_pago", args=[liq.pk]),
            {
                "fecha": timezone.localdate().isoformat(),
                "monto": "800001",
                "medio_pago": PagoRemuneracion.MedioPago.TRANSFERENCIA,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(liq.pagos.count(), 0)

    def test_anular_pago_desde_ui(self):
        liq = self._liquidacion_validada()
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        pago = liq.pagos.get()
        response = self.client.post(
            reverse("remuneraciones:pago_anular", args=[pago.pk]),
            {"motivo": "Error de digitación"},
        )
        self.assertRedirects(
            response,
            reverse("remuneraciones:liquidacion_detalle", args=[liq.pk]),
        )
        pago.refresh_from_db()
        self.assertTrue(pago.anulado)


class PagoResumenTests(Rem005C01Base):
    def test_resumen_anual_ignora_pagos_anulados(self):
        liq = self._liquidacion_validada()
        pago = registrar_pago(
            liq,
            fecha=date(2026, 8, 28),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        anular_pago(pago, motivo="Error", usuario=self.user)
        registrar_pago(
            liq,
            fecha=date(2026, 8, 28),
            monto=Decimal("800000"),
            usuario=self.user,
        )
        pagado = resumen_anual(2026, metrica=METRICA_PAGADO)
        self.assertEqual(pagado["total_anual"], Decimal("800000.00"))
