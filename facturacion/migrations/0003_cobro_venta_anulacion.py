from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("facturacion", "0002_pago_compra_anulacion")]
    operations = [
        migrations.AddField(model_name="cobrodocumentotributario", name="anulado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="cobrodocumentotributario", name="anulado_en", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="cobrodocumentotributario", name="motivo_anulacion", field=models.TextField(blank=True)),
        migrations.AddField(model_name="cobrodocumentotributario", name="anulado_por", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cobros_documento_anulados", to=settings.AUTH_USER_MODEL)),
    ]
