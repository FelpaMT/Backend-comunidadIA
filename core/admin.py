from django.contrib import admin
from .models import User, Educator, Publication, Commentary, Subscription, RefreshToken, Image
from django.contrib.auth.hashers import make_password, identify_hasher

class UserCreate(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role")
    fields = ("name", "email", "role", "password")
    search_fields = ("email", "name")

    def save_model(self, request, obj, form, change):
        pwd = form.cleaned_data.get("password")
        if pwd:
            try:
                identify_hasher(pwd)
                obj.password = pwd
            except Exception:
                obj.password = make_password(pwd)
        super().save_model(request, obj, form, change)

admin.site.register(User, UserCreate)
admin.site.register(Educator)
admin.site.register(Publication)
admin.site.register(Commentary)
admin.site.register(Subscription)
admin.site.register(RefreshToken)
admin.site.register(Image)
