from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("facturacion", "0001_initial")]
    operations = [
        migrations.AddField(model_name="pagodocumentocompra", name="anulado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="pagodocumentocompra", name="anulado_en", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="pagodocumentocompra", name="motivo_anulacion", field=models.TextField(blank=True)),
        migrations.AddField(model_name="pagodocumentocompra", name="anulado_por", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_compra_anulados", to=settings.AUTH_USER_MODEL)),
    ]
