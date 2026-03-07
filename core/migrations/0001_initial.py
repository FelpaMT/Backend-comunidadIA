from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

def enable_pg_trgm(apps, schema_editor):
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(enable_pg_trgm),
        # (Django generará automáticamente las CreateModel por los modelos)
    ]
