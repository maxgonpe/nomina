from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("impuestos", "0001_initial")]
    operations = [migrations.AlterField(model_name="periodoimpuesto", name="estado", field=models.CharField(choices=[("BORRADOR", "Borrador"), ("CALCULADO", "Calculado"), ("VALIDADO", "Validado"), ("DECLARADO", "Declarado"), ("PAGADO", "Pagado"), ("CERRADO", "Cerrado")], default="BORRADOR", max_length=15))]
