from rest_framework import serializers
from .models import User, Educator, Publication, Commentary, Subscription, RefreshToken, Role, PublicationType, Image, Category
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import OpenApiTypes, extend_schema_field

class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role"]

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=12, trim_whitespace=False)

    nick_name = serializers.CharField(
        required=True,
        validators=[UniqueValidator(
            queryset=Educator.objects.all(),
            message="Ya existe educator con este nick_name."
        )]
    )
    class Meta:
        model = User
        fields = ["id", "name", "email", "password", "role", "nick_name"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_password(self, value):
        candidate = User(
            name=self.initial_data.get("name", ""),
            email=self.initial_data.get("email", ""),
        )
        try:
            validate_password(value, candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def create(self, validated):
        password = validated.pop("password")
        nick = validated.pop("nick_name", None)
        user = User(**validated)
        user.set_password(password)
        user.save()
        # Crear Educator automáticamente solo si role=EDUCATOR
        if user.role == Role.EDUCATOR:
            Educator.objects.create(id=user.id, user=user, nick_name=nick)
        return user

class EducatorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Educator
        fields = [
            "id", "nick_name", "bio", "institution", "specialty",
            "avatar", "website", "linkedin_url", "followers_count",
            "following_count", "user"
        ]

class EducatorProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", required=False)
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = Educator
        fields = [
            "id", "nick_name", "name", "email", "role", "bio",
            "institution", "specialty", "avatar", "website", "linkedin_url"
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if "name" in user_data:
            instance.user.name = user_data["name"]
            instance.user.save(update_fields=["name"])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class EducatorPublicSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodNested if False else serializers.SerializerMethodField()

    class Meta:
        model = Educator
        fields = [
            "id", "nick_name", "bio", "institution", "specialty",
            "avatar", "website", "linkedin_url", "followers_count",
            "following_count", "is_following", "user"
        ]

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        me_edu = getattr(request.user, "educator", None)
        if not me_edu:
            return False
        return Subscription.objects.filter(subscriber=me_edu, subscribed=obj).exists()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description"]

class ImageSerializer(serializers.ModelSerializer):
    absolute_url = serializers.CharField(read_only=True)

    class Meta:
        model = Image
        fields = ["id", "file", "url", "absolute_url", "caption", "created_at"]

class PublicationSerializer(serializers.ModelSerializer):
    writer = EducatorSerializer(source="educator", read_only=True)
    category = CategorySerializer(read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    images_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Publication
        fields = [
            "id", "title", "publication_type", "content_url",
            "created_at", "updated_at", "writer", "category",
            "images", "comments_count", "images_count"
        ]

class PublicationCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    publication_type = serializers.ChoiceField(choices=PublicationType.choices)
    content = serializers.CharField()
    category_id = serializers.IntegerField(required=False, allow_null=True)

class EducatorWithFollowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nick_name = serializers.CharField()
    bio = serializers.CharField(allow_blank=True, required=False)
    institution = serializers.CharField(allow_blank=True, required=False)
    specialty = serializers.CharField(allow_blank=True, required=False)
    avatar = serializers.CharField(allow_blank=True, required=False)
    website = serializers.CharField(allow_blank=True, required=False)
    linkedin_url = serializers.CharField(allow_blank=True, required=False)
    followers_count = serializers.IntegerField(default=0)
    following_count = serializers.IntegerField(default=0)
    user = UserSerializer()

    followed_by_me = serializers.BooleanField()
    following_me = serializers.BooleanField()
    is_following = serializers.BooleanField(default=False)

class EducatorDetailWithPublicationsSerializer(EducatorWithFollowSerializer):
    publications = PublicationSerializer(many=True)

class SubscriptionToggleSerializer(serializers.Serializer):
    subscribed = serializers.BooleanField()
    detail = serializers.CharField()

class CommentarySerializer(serializers.ModelSerializer):
    writer = EducatorSerializer(source="educator", read_only=True)

    class Meta:
        model = Commentary
        fields = ["id", "content", "created_at", "updated_at", "publication", "writer"]

class CommentaryCreateSerializer(serializers.Serializer):
    content = serializers.CharField()

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["subscriber", "subscribed"]

# ---- Swagger input/output helpers ----

from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class DeleteMeSerializer(serializers.Serializer):
    password = serializers.CharField()

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "email"]
        extra_kwargs = {
            "email": {"error_messages": {"unique": "Ya existe user con este email."}},
        }

class PublicationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False)
    publication_type = serializers.ChoiceField(choices=["ARTICLE", "FORUM"], required=False)
    content = serializers.CharField(required=False)
    category_id = serializers.IntegerField(required=False, allow_null=True)

class CommentaryUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)

# ---- Respuestas estandarizadas para Swagger ----
from rest_framework import serializers
from .models import User, Educator, Publication

class AccessTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField()

class RefreshResponseSerializer(serializers.Serializer):
    new_access_token = serializers.CharField()

class SignupResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    user = UserSerializer(required=False)
    access_token = serializers.CharField(required=False)

class MeEducatorDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nick_name = serializers.CharField(allow_null=True)
    user = UserSerializer()
    publications = PublicationSerializer(many=True)

class EducatorUserUpdateSerializer(serializers.Serializer):
    nick_name = serializers.CharField(
        required=False,
        validators=[UniqueValidator(
            queryset=Educator.objects.all(),
            message="Ya existe educator con este nick_name."
        )]
    )
    name = serializers.CharField(required=False)
    email = serializers.CharField(
        required=False,
        validators=[UniqueValidator(
            queryset=User.objects.all(),
            message="Ya existe educator con este email."
        )]
    )

class ImageUploadRequestSerializer(serializers.Serializer):
    publication_id = serializers.IntegerField()
    file = serializers.ImageField()


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=False, allow_blank=True)
    token = serializers.CharField(required=False, allow_blank=True)

class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=12, trim_whitespace=False)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

class AIChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, help_text="Consulta o mensaje enviado por el usuario al Asistente IA.")
    publication_id = serializers.IntegerField(required=False, allow_null=True, default=None, help_text="ID de la publicación para inyectar contexto pedagógico (opcional).")
    history = serializers.ListField(child=serializers.DictField(), required=False, default=list, help_text="Historial conversacional previo.")

class AIChatResponseSerializer(serializers.Serializer):
    response = serializers.CharField(help_text="Respuesta generada por el Tutor IA Gemini.")
    context_used = serializers.BooleanField(help_text="Indica si se utilizó el contexto pedagógico de la publicación especificada.")

