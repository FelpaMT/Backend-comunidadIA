from django.dispatch import receiver
from django.db.models.signals import post_delete
from .models import Publication, Image
from .storage import delete_publication_html
@receiver(post_delete, sender=Publication)
def delete_publication_file_on_delete(sender, instance, **kwargs):
    delete_publication_html(instance.content_url)
    
@receiver(post_delete, sender=Image)
def delete_image_file(sender, instance, **kwargs):
    
    storage = instance.file.storage
    if storage.exists(instance.file.name):
        storage.delete(instance.file.name)