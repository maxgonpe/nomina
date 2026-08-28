from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("impuestos", "0002_periodo_validado")]
    operations = [
        migrations.AddField(model_name="pagoimpuesto", name="medio_pago", field=models.CharField(blank=True, max_length=50)),
        migrations.AddField(model_name="pagoimpuesto", name="anulado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="pagoimpuesto", name="anulado_en", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="pagoimpuesto", name="motivo_anulacion", field=models.TextField(blank=True)),
        migrations.AddField(model_name="pagoimpuesto", name="anulado_por", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_impuestos_anulados", to=settings.AUTH_USER_MODEL)),
    ]
