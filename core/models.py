from django.db import models
from django.contrib.auth.hashers import make_password
import os
from django.conf import settings

class Role(models.TextChoices):
    EDUCATOR = "EDUCATOR", "EDUCATOR"
    ADMIN = "ADMIN", "ADMIN"

class PublicationType(models.TextChoices):
    ARTICLE = "ARTICLE", "ARTICLE"
    FORUM = "FORUM", "FORUM"

class User(models.Model):
    # Tabla users
    name = models.CharField(max_length=255, null=False)
    email = models.EmailField(unique=True, max_length=100, null=False)
    password = models.CharField(max_length=255, null=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDUCATOR, null=False)

    def set_password(self, raw: str):
        self.password = make_password(raw)
        
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
    
class Educator(models.Model):
    id = models.BigAutoField(primary_key=True)
    nick_name = models.CharField(max_length=255, unique=True, null=True, db_column="nick_name")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="educator", db_column="user_id")
    
class Publication(models.Model):
    title = models.CharField(max_length=255, null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, null=False, db_column="updatedAt")
    educator = models.ForeignKey(Educator, on_delete=models.CASCADE, related_name="publications", db_column="educator_id")
    publication_type = models.CharField(max_length=20, choices=PublicationType.choices, db_column="publication_type")
    content_url = models.CharField(max_length=1000, null=False, db_column="content_url")

def image_upload_path(instance, filename):
    # El filename NO se usa — lo reemplazamos por el id luego en save()
    return f"images/{filename}"  # temporal
    # Luego en save() renombramos el archivo al ID real
    
class Image(models.Model):
    publication = models.ForeignKey(
        "Publication",
        related_name="images",
        on_delete=models.CASCADE
    )
    file = models.ImageField(upload_to=image_upload_path)
    url = models.URLField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Guardamos primero para obtener ID
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            old_path = self.file.path
            ext = os.path.splitext(old_path)[1]  # .png, .jpg, etc
            new_name = f"{self.pk}{ext}"  # filename = id.ext
            new_path = os.path.join(os.path.dirname(old_path), new_name)

            # Renombrar archivo físico
            os.rename(old_path, new_path)

            # Actualizar file field
            self.file.name = f"images/{new_name}"

            # Generar URL pública
            self.url = f"{settings.DOMAIN}{settings.MEDIA_URL}{self.file.name}"

            # Guardar cambios
            super().save(update_fields=["file", "url"])

class Commentary(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=False, db_column="createdAt")
    updated_at = models.DateTimeField(auto_now=True, null=False, db_column="updatedAt")
    content = models.TextField(max_length=2000, null=False)
    educator = models.ForeignKey(Educator, on_delete=models.CASCADE, related_name="commentaries", db_column="educator_id")
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="commentaries", db_column="publication_id")

class Subscription(models.Model):
    # Many-to-many Educator<->Educator con PK compuesta (subscriber_id, subscribed_id)
    subscriber = models.ForeignKey(Educator, on_delete=models.CASCADE, related_name="following", db_column="subscriber_id")
    subscribed = models.ForeignKey(Educator, on_delete=models.CASCADE, related_name="followers", db_column="subscribed_id")

    class Meta:
        unique_together = ("subscriber", "subscribed")

class RefreshToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="refresh_token")
    token = models.CharField(max_length=512, unique=True)
    expiry_date = models.DateTimeField()
