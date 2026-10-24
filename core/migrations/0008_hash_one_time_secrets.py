from django.db import migrations, models


def revoke_legacy_tokens(apps, schema_editor):
    """Remove plaintext tokens before the columns start storing HMAC digests."""
    apps.get_model("core", "RefreshToken").objects.all().delete()
    apps.get_model("core", "EmailVerificationToken").objects.all().delete()
    apps.get_model("core", "PasswordResetToken").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_category_description_image_caption"),
    ]

    operations = [
        migrations.RunPython(revoke_legacy_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="refreshtoken",
            name="token",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name="emailverificationtoken",
            name="code",
            field=models.CharField(max_length=64),
        ),
        migrations.AlterField(
            model_name="emailverificationtoken",
            name="token",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AddField(
            model_name="emailverificationtoken",
            name="attempts",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="passwordresettoken",
            name="token",
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
