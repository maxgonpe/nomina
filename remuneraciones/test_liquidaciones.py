import inspect
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CentroCosto, ParametroNegocio, ParametroValor
from remuneraciones.models import (
    ConceptoRemuneracion,
    HoraExtra,
    LiquidacionMensual,
    MovimientoRemuneracion,
    PagoRemuneracion,
)
from remuneraciones.services.finiquitos import validar as validar_finiquito
from remuneraciones.services.finiquitos import registrar as registrar_finiquito
from remuneraciones.services.liquidaciones import (
    anular,
    calcular,
    calcular_periodo,
    marcar_pagada,
    validar,
)
from remuneraciones.services.pagos import registrar_pago
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


class Rem005Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("rrhh", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="remuneraciones",
            codename__in=[
                "view_liquidacionmensual",
                "change_liquidacionmensual",
                "add_pagoremuneracion",
                "view_periodoremuneracion",
                "change_periodoremuneracion",
                "add_periodoremuneracion",
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
        self.contrato = Contrato.objects.create(
            trabajador=self.trabajador,
            cargo=self.cargo,
            centro_costo=self.cc,
            fecha_inicio=date(2026, 1, 1),
            sueldo_base_inicial=Decimal("800000"),
        )
        self.periodo = crear(anio=2026, mes=8, usuario=self.user)
        abrir(self.periodo, usuario=self.user)

    def _mov(self, codigo, monto):
        return registrar_movimiento(
            trabajador=self.trabajador,
            periodo=self.periodo,
            concepto=ConceptoRemuneracion.objects.get(codigo=codigo),
            monto=Decimal(str(monto)),
            usuario=self.user,
        )


class LiquidacionMotorTests(Rem005Base):
    def test_sin_horas_extra_ni_movimientos(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.CALCULADA)
        self.assertEqual(liq.sueldo_base_snapshot, Decimal("800000.00"))
        self.assertEqual(liq.cargo_codigo_snapshot, "MAESTRO")
        self.assertEqual(liq.centro_costo_codigo_snapshot, "EGC")
        self.assertEqual(liq.dias_trabajados, Decimal("30.00"))
        self.assertEqual(liq.horas_extra_total, Decimal("0.00"))
        sueldo = liq.movimientos.get(concepto__codigo="SUELDO_BASE")
        self.assertEqual(sueldo.monto, Decimal("800000.00"))
        self.assertEqual(sueldo.origen, MovimientoRemuneracion.Origen.CALCULADO)
        self.assertFalse(
            liq.movimientos.filter(concepto__codigo="HORAS_EXTRA").exists()
        )
        self.assertFalse(
            liq.movimientos.filter(concepto__codigo="INASISTENCIA").exists()
        )
        self.assertEqual(liq.total_haberes, Decimal("800000.00"))
        self.assertEqual(liq.total_descuentos, Decimal("0.00"))
        self.assertEqual(liq.total_liquidado, Decimal("800000.00"))
        self.assertEqual(liq.total_a_pagar, liq.total_liquidado)
        self.assertFalse(liq.requiere_recalculo)

    def test_con_horas_extra_usa_factor_parametro(self):
        HoraExtra.objects.create(
            trabajador=self.trabajador,
            periodo=self.periodo,
            fecha=date(2026, 8, 10),
            horas=Decimal("2.00"),
        )
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertEqual(liq.horas_extra_total, Decimal("2.00"))
        self.assertEqual(liq.valor_hora_extra, Decimal("6363.6000"))
        self.assertEqual(liq.monto_horas_extra, Decimal("12727.20"))
        he = liq.movimientos.get(concepto__codigo="HORAS_EXTRA")
        self.assertEqual(he.monto, Decimal("12727.20"))
        self.assertEqual(liq.total_haberes, Decimal("812727.20"))
        fuente = inspect.getsource(calcular)
        self.assertNotIn("0.0079545", fuente)

    def test_faltas_descuentan_sin_reducir_el_sueldo_pactado(self):
        liq = calcular(
            self.trabajador,
            self.periodo,
            usuario=self.user,
            dias_fallados=Decimal("2"),
        )
        self.assertEqual(liq.dias_fallados, Decimal("2.00"))
        self.assertEqual(liq.dias_trabajados, Decimal("28.00"))
        self.assertEqual(
            liq.movimientos.get(concepto__codigo="SUELDO_BASE").monto,
            Decimal("800000.00"),
        )
        inas = liq.movimientos.get(concepto__codigo="INASISTENCIA")
        self.assertEqual(inas.monto, (liq.valor_dia * Decimal("2")).quantize(
            Decimal("0.01")
        ))
        self.assertEqual(
            liq.total_liquidado,
            liq.total_haberes - liq.total_descuentos,
        )

    def test_bono_y_anticipo_entran_en_totales(self):
        self._mov("BONO_PRODUCCION", "50000")
        self._mov("ANTICIPO", "100000")
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertEqual(
            liq.movimientos.get(concepto__codigo="BONO_PRODUCCION").monto,
            Decimal("50000.00"),
        )
        self.assertEqual(
            liq.movimientos.get(concepto__codigo="ANTICIPO").monto,
            Decimal("100000.00"),
        )
        self.assertEqual(liq.total_haberes, Decimal("850000.00"))
        self.assertEqual(liq.total_descuentos, Decimal("100000.00"))
        self.assertEqual(liq.total_a_pagar, Decimal("750000.00"))

    def test_varios_conceptos_no_agregan_columnas(self):
        campos = {f.name for f in LiquidacionMensual._meta.get_fields()}
        self.assertNotIn("aguinaldo", campos)
        self.assertNotIn("bono_produccion", campos)
        self._mov("AGUINALDO", "40000")
        self._mov("ALOJAMIENTO", "20000")
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertEqual(liq.total_haberes, Decimal("860000.00"))

    def test_anexo_de_agosto_no_reescribe_enero(self):
        enero = crear(anio=2026, mes=1, usuario=self.user)
        abrir(enero, usuario=self.user)
        liq_ene = calcular(self.trabajador, enero, usuario=self.user)
        self.assertEqual(liq_ene.sueldo_base_snapshot, Decimal("800000.00"))
        AnexoContrato.objects.create(
            contrato=self.contrato,
            fecha_documento=date(2026, 8, 1),
            fecha_vigencia=date(2026, 8, 1),
            tipo=AnexoContrato.Tipo.CAMBIO_SUELDO,
            nuevo_sueldo_base=Decimal("950000"),
        )
        liq_ene = calcular(self.trabajador, enero, usuario=self.user)
        self.assertEqual(liq_ene.sueldo_base_snapshot, Decimal("800000.00"))
        liq_ago = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertEqual(liq_ago.sueldo_base_snapshot, Decimal("950000.00"))

    def test_finiquito_validado_no_se_duplica_al_recalcular(self):
        fin = registrar_finiquito(
            trabajador=self.trabajador,
            contrato=self.contrato,
            periodo=self.periodo,
            fecha=date(2026, 8, 20),
            monto=Decimal("500000"),
            usuario=self.user,
        )
        validar_finiquito(fin, usuario=self.user)
        calcular(self.trabajador, self.periodo, usuario=self.user)
        calcular(self.trabajador, self.periodo, usuario=self.user)
        finiquitos = MovimientoRemuneracion.objects.filter(
            concepto__codigo="FINIQUITO",
            liquidacion__trabajador=self.trabajador,
            liquidacion__periodo=self.periodo,
        )
        self.assertEqual(finiquitos.count(), 1)
        self.assertEqual(finiquitos.get().monto, Decimal("500000.00"))

    def test_recalculo_no_borra_movimientos_manuales(self):
        self._mov("AGUINALDO", "35000")
        calcular(self.trabajador, self.periodo, usuario=self.user)
        calcular(self.trabajador, self.periodo, usuario=self.user)
        manual = MovimientoRemuneracion.objects.get(
            concepto__codigo="AGUINALDO"
        )
        self.assertEqual(manual.origen, MovimientoRemuneracion.Origen.MANUAL)
        self.assertEqual(manual.monto, Decimal("35000.00"))

    def test_colacion_proporcional_si_hay_parametro(self):
        parametro = ParametroNegocio.objects.get(codigo="VALOR_COLACION_MENSUAL")
        ParametroValor.objects.create(
            parametro=parametro,
            valor=Decimal("30000"),
            vigencia_desde=date(2026, 1, 1),
            vigencia_hasta=date(2026, 12, 31),
        )
        liq = calcular(
            self.trabajador,
            self.periodo,
            usuario=self.user,
            dias_fallados=Decimal("2"),
        )
        colacion = liq.movimientos.get(concepto__codigo="COLACION")
        self.assertEqual(colacion.monto, Decimal("28000.00"))

    def test_sin_parametro_de_colacion_no_falla(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.assertFalse(
            liq.movimientos.filter(concepto__codigo="COLACION").exists()
        )

    def test_pagada_exige_pago_registrado(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        validar(liq, usuario=self.user)
        with self.assertRaises(ValidationError):
            marcar_pagada(liq, usuario=self.user)
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("100000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        with self.assertRaises(ValidationError):
            marcar_pagada(liq, usuario=self.user)
        registrar_pago(
            liq,
            fecha=timezone.localdate(),
            monto=Decimal("700000"),
            usuario=self.user,
        )
        liq.refresh_from_db()
        marcar_pagada(liq, usuario=self.user)
        liq.refresh_from_db()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.PAGADA)
        self.assertEqual(liq.total_pagado, Decimal("800000.00"))

    def test_periodo_cerrado_no_recalcula(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        marcar_calculado(self.periodo, usuario=self.user)
        validar_periodo(self.periodo, usuario=self.user)
        cerrar(self.periodo, usuario=self.user)
        with self.assertRaises(ValidationError):
            calcular(self.trabajador, self.periodo, usuario=self.user)
        with self.assertRaises(ValidationError):
            anular(liq, usuario=self.user)

    def test_calcular_periodo_sin_trabajadores(self):
        previo = crear(anio=2025, mes=7, usuario=self.user)
        abrir(previo, usuario=self.user)
        ok, errores = calcular_periodo(previo, usuario=self.user)
        self.assertEqual(ok, [])
        self.assertEqual(errores, [])


class LiquidacionVistaTests(Rem005Base):
    def test_lista_y_detalle(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        response = self.client.get(reverse("remuneraciones:liquidacion_lista"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana Pérez")
        response = self.client.get(liq.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sueldo (snapshot)")
        self.assertContains(response, "MAESTRO")
        self.assertContains(response, "EGC")

    def test_calcular_desde_el_periodo(self):
        response = self.client.post(
            reverse("remuneraciones:periodo_calcular", args=[self.periodo.pk])
        )
        self.assertRedirects(
            response,
            reverse("remuneraciones:periodo_detalle", args=[self.periodo.pk]),
        )
        liq = LiquidacionMensual.objects.get()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.CALCULADA)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.estado, "CALCULADO")

    def test_validar_pago_y_marcar_pagada_desde_ui(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.client.post(
            reverse("remuneraciones:liquidacion_validar", args=[liq.pk])
        )
        liq.refresh_from_db()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.VALIDADA)
        self.client.post(
            reverse("remuneraciones:liquidacion_pago", args=[liq.pk]),
            {
                "fecha": timezone.localdate().isoformat(),
                "monto": "800000",
                "medio_pago": PagoRemuneracion.MedioPago.TRANSFERENCIA,
            },
        )
        self.assertEqual(liq.pagos.count(), 1)
        self.client.post(
            reverse("remuneraciones:liquidacion_pagar", args=[liq.pk])
        )
        liq.refresh_from_db()
        self.assertEqual(liq.estado, LiquidacionMensual.Estado.PAGADA)

    def test_dias_fallados_desde_ui(self):
        liq = calcular(self.trabajador, self.periodo, usuario=self.user)
        self.client.post(
            reverse("remuneraciones:liquidacion_calcular", args=[liq.pk]),
            {"dias_fallados": "2"},
        )
        liq.refresh_from_db()
        self.assertEqual(liq.dias_fallados, Decimal("2.00"))
        self.assertTrue(
            liq.movimientos.filter(concepto__codigo="INASISTENCIA").exists()
        )
