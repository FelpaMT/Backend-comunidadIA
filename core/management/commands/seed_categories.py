from django.core.management.base import BaseCommand
from core.models import Category

INITIAL_CATEGORIES = [
    {"name": "Matemática",  "slug": "matematica"},
    {"name": "Ciencias",    "slug": "ciencias"},
    {"name": "Lenguaje",    "slug": "lenguaje"},
    {"name": "Historia",    "slug": "historia"},
    {"name": "Arte",        "slug": "arte"},
    {"name": "Tecnología",  "slug": "tecnologia"},
    {"name": "Otra",        "slug": "otra"},
]


class Command(BaseCommand):
    help = "Inserta las categorías iniciales de publicaciones."

    def handle(self, *args, **options):
        created = 0
        for cat in INITIAL_CATEGORIES:
            _, was_created = Category.objects.get_or_create(
                slug=cat["slug"],
                defaults={"name": cat["name"]},
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Creada: {cat['name']}")
            else:
                self.stdout.write(f"  Ya existe: {cat['name']}")
        self.stdout.write(self.style.SUCCESS(f"\nListo. {created} categorías nuevas insertadas."))
