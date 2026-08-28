from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("finanzas", "0003_fin002_pago_remuneracion"), ("facturacion", "0003_cobro_venta_anulacion")]
    operations = [
        migrations.AddField(model_name="movimientofinanciero", name="cobro_documento", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimientos_financieros", to="facturacion.cobrodocumentotributario")),
        migrations.AddConstraint(model_name="movimientofinanciero", constraint=models.UniqueConstraint(fields=("origen", "cobro_documento"), name="uq_mov_fin_cobro_documento")),
    ]
