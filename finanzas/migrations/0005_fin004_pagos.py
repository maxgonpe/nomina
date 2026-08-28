from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("finanzas", "0004_fin003_cobro_documento"), ("facturacion", "0003_cobro_venta_anulacion"), ("impuestos", "0003_pago_impuesto_auditoria")]
    operations = [
        migrations.AddField(model_name="movimientofinanciero", name="pago_compra", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimientos_financieros", to="facturacion.pagodocumentocompra")),
        migrations.AddField(model_name="movimientofinanciero", name="pago_impuesto", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimientos_financieros", to="impuestos.pagoimpuesto")),
        migrations.AddConstraint(model_name="movimientofinanciero", constraint=models.UniqueConstraint(fields=("origen", "pago_compra"), name="uq_mov_fin_pago_compra")),
        migrations.AddConstraint(model_name="movimientofinanciero", constraint=models.UniqueConstraint(fields=("origen", "pago_impuesto"), name="uq_mov_fin_pago_impuesto")),
    ]
