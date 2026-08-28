from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("finanzas", "0002_catalogo_categorias"), ("remuneraciones", "0001_initial")]
    operations = [migrations.AddField(model_name="movimientofinanciero", name="pago_remuneracion", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movimientos_financieros", to="remuneraciones.pagoremuneracion")), migrations.AddConstraint(model_name="movimientofinanciero", constraint=models.UniqueConstraint(fields=("origen", "pago_remuneracion"), name="uq_mov_fin_pago_remuneracion"))]
