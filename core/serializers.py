from rest_framework import serializers
from .models import User, Educator, Publication, Commentary, Subscription, RefreshToken, Role, PublicationType, Image
from rest_framework.validators import UniqueValidator
from drf_spectacular.utils import OpenApiTypes, extend_schema_field

class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role"]

class UserCreateSerializer(serializers.ModelSerializer):
    
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
    class Meta:
        model = Educator
        fields = ["id", "nick_name", "user"]

class PublicationSerializer(serializers.ModelSerializer):
    writer = EducatorSerializer(source="educator", read_only=True)
    class Meta:
        model = Publication
        fields = ["id", "title", "publication_type", "content_url", "created_at", "updated_at", "writer"]

class PublicationCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    publication_type = serializers.ChoiceField(choices=PublicationType.choices)
    content = serializers.CharField()

class EducatorWithFollowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nick_name = serializers.CharField()
    user = UserSerializer()

    followed_by_me = serializers.BooleanField()
    following_me = serializers.BooleanField()
    
class EducatorDetailWithPublicationsSerializer(EducatorWithFollowSerializer):
    publications = PublicationSerializer(many=True)

class CommentarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Commentary
        fields = ["id", "content", "created_at", "updated_at", "publication"]

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

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

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

class CommentaryUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(required=True)

# ---- Respuestas estandarizadas para Swagger ----
from rest_framework import serializers
from .models import User, Educator, Publication

class TokenPairSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()

class RefreshResponseSerializer(serializers.Serializer):
    new_access_token = serializers.CharField()

class SignupResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()

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


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ["id", "file", "url", "created_at"]