from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountsubscriptionstate",
            name="billing_cycle",
            field=models.CharField(
                choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
                default="monthly",
                max_length=20,
            ),
        ),
    ]
