from django.db.models import Q, F
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiRequest
from .models import User, Educator, Publication, Commentary, Subscription, Role, PublicationType, RefreshToken, Image, Category, EmailVerificationToken, PasswordResetToken
# Arriba en views.py (importa los nuevos serializers)
from .serializers import (
    UserSerializer, UserCreateSerializer, EducatorSerializer, EducatorProfileSerializer, EducatorPublicSerializer, SubscriptionToggleSerializer, MeEducatorDetailSerializer, EducatorWithFollowSerializer, EducatorDetailWithPublicationsSerializer,
    PublicationSerializer, PublicationCreateSerializer,
    CommentarySerializer, CommentaryCreateSerializer,
    SubscriptionSerializer,
    LoginSerializer, DeleteMeSerializer,
    AdminUserUpdateSerializer,
    PublicationUpdateSerializer, CommentaryUpdateSerializer,
    MessageSerializer,
    AccessTokenSerializer,
    RefreshResponseSerializer,
    EducatorUserUpdateSerializer,
    ImageUploadRequestSerializer, ImageSerializer,
    CategorySerializer,
    VerifyEmailSerializer, ResendVerificationSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    SignupResponseSerializer, AIChatRequestSerializer, AIChatResponseSerializer
)
from .gemini_service import generate_chat_response
from .permissions import IsAdmin, IsOwnerEducatorObject
from .jwt_utils import generate_access_token, generate_and_store_refresh
from .storage import save_publication_html, update_publication_html, get_publication_html
from .email_utils import (
    create_email_verification_token, send_verification_email,
    create_password_reset_token, send_password_reset_email
)
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser

# -------- Helpers --------
def require_offset_limit(request):
    try:
        offset = int(request.query_params.get("offset", ""))
        limit = int(request.query_params.get("limit", ""))
        return offset, limit
    except Exception:
        raise ValueError("Los parámetros offset y limit son obligatorios y deben ser enteros.")

def paginated(qs, offset, limit):
    return qs[offset: offset + limit]

def get_me_educator(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "educator", None)

# -------- Auth --------
def _set_refresh_cookie(response, token):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        token,
        max_age=int(settings.JWT_CONFIG["REFRESH_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path="/api/auth/",
    )
    return response


def _clear_refresh_cookie(response):
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path="/api/auth/",
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
    return response


class AuthSignupView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        request=UserCreateSerializer,
        responses={201: UserSerializer},
        description="Crea usuario docente y envía código de verificación al correo."
    )
    def post(self, request):
        data = request.data.copy()
        if data.get("role") == "ADMIN":
            return Response({"detail":"No se puede crear ADMIN aquí."}, status=400)

        ser = UserCreateSerializer(data=data)
        if ser.is_valid():
            user = ser.save()
            user.is_verified = False
            user.save(update_fields=["is_verified"])

            # Generar token y enviar correo de verificación
            ver_token = create_email_verification_token(user)
            send_verification_email(user, ver_token)

            return Response({
                "detail": "Usuario registrado exitosamente. Por favor verifica tu correo electrónico con el código enviado.",
                "email": user.email,
                "requires_verification": True,
            }, status=201)
        return Response(ser.errors, status=400)

class AuthVerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        request=VerifyEmailSerializer,
        responses={200: SignupResponseSerializer},
        description="Verifica el correo con el código de 6 dígitos o el token de enlace."
    )
    def post(self, request):
        ser = VerifyEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        code = ser.validated_data.get("code", "").strip()
        token = ser.validated_data.get("token", "").strip()

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "Usuario no encontrado."}, status=404)

        if user.is_verified:
            return Response({"detail": "Tu cuenta ya está verificada. Inicia sesión para continuar."}, status=200)

        ver_token = None
        if token:
            ver_token = EmailVerificationToken.objects.filter(user=user, token=token).first()
        elif code:
            ver_token = EmailVerificationToken.objects.filter(user=user, code=code).first()

        if not ver_token or not ver_token.is_valid():
            return Response({"detail": "Código o enlace de verificación inválido o expirado."}, status=400)

        ver_token.is_used = True
        ver_token.save(update_fields=["is_used"])

        user.is_verified = True
        user.save(update_fields=["is_verified"])

        access = generate_access_token(user)
        refresh, _ = generate_and_store_refresh(user)

        response = Response({
            "detail": "Cuenta verificada exitosamente.",
            "user": UserSerializer(user).data,
            "access_token": access,
        }, status=200)
        return _set_refresh_cookie(response, refresh)

class AuthResendVerificationView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        request=ResendVerificationSerializer,
        responses={200: MessageSerializer},
        description="Reenvía el código de verificación al correo."
    )
    def post(self, request):
        ser = ResendVerificationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "Si el correo está registrado, se ha enviado un nuevo código."}, status=200)

        if user.is_verified:
            return Response({"detail": "Esta cuenta ya se encuentra verificada."}, status=400)

        ver_token = create_email_verification_token(user)
        send_verification_email(user, ver_token)
        return Response({"detail": "Nuevo código de verificación enviado a tu correo."}, status=200)

class AuthForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        request=ForgotPasswordSerializer,
        responses={200: MessageSerializer},
        description="Solicita el enlace de recuperación de contraseña."
    )
    def post(self, request):
        ser = ForgotPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email).first()
        if user:
            reset_token = create_password_reset_token(user)
            send_password_reset_email(user, reset_token)

        return Response({
            "detail": "Si el correo está registrado, recibirás un enlace de recuperación en los próximos minutos."
        }, status=200)

class AuthResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        request=ResetPasswordSerializer,
        responses={200: MessageSerializer},
        description="Restablece la contraseña utilizando el token recibido."
    )
    def post(self, request):
        ser = ResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        token_str = ser.validated_data["token"].strip()
        new_pwd = ser.validated_data["new_password"]

        reset_token = PasswordResetToken.objects.filter(token=token_str).first()
        if not reset_token or not reset_token.is_valid():
            return Response({"detail": "El enlace de recuperación es inválido o ha expirado."}, status=400)

        user = reset_token.user
        try:
            validate_password(new_pwd, user)
        except DjangoValidationError as exc:
            return Response({"new_password": list(exc.messages)}, status=400)
        user.set_password(new_pwd)
        user.save(update_fields=["password"])
        RefreshToken.objects.filter(user=user).delete()

        reset_token.is_used = True
        reset_token.save(update_fields=["is_used"])

        return Response({
            "detail": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión con tu nueva contraseña."
        }, status=200)

class AuthLoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    @extend_schema(
        tags=["Auth"],
        request=LoginSerializer,
        responses={200: AccessTokenSerializer},
        description="Login con email y password."
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        pwd = request.data.get("password")
        user = User.objects.filter(email__iexact=email).first()
        if not user or not check_password(pwd, user.password):
            return Response({"detail":"Credenciales inválidas"}, status=401)
        if not user.is_verified and user.role != Role.ADMIN:
            # Reenviar token si es necesario
            ver_token = create_email_verification_token(user)
            send_verification_email(user, ver_token)
            return Response({
                "detail": "Debes verificar tu correo electrónico antes de iniciar sesión. Hemos enviado un nuevo código a tu correo.",
                "requires_verification": True,
                "email": user.email
            }, status=403)
        access = generate_access_token(user)
        refresh, _ = generate_and_store_refresh(user)
        response = Response({"access_token": access}, status=200)
        return _set_refresh_cookie(response, refresh)

class AuthLogoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=None,
        responses={200: MessageSerializer},
        description="Elimina el refresh token en DB para invalidar sesiones."
    )
    def post(self, request):
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not token:
            return _clear_refresh_cookie(Response({"detail": "Sesión cerrada"}, status=200))

        ref = RefreshToken.objects.filter(token=token).first()
        if ref:
            ref.delete()
        return _clear_refresh_cookie(Response({"detail": "OK"}, status=200))

class AuthRefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=None,
        responses={200: RefreshResponseSerializer},
        description="Recibe access_token y retorna uno nuevo (usa refresh guardado en DB)."
    )
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not refresh_token:
            return _clear_refresh_cookie(Response({"detail": "Sesión no disponible"}, status=401))

        ref = RefreshToken.objects.filter(token=refresh_token).first()
        if not ref:
            return Response({"detail": "Refresh token inválido"}, status=401)
        if ref.expiry_date <= timezone.now():
            ref.delete()
            return _clear_refresh_cookie(Response({"detail": "Refresh token expirado"}, status=401))

        user = ref.user
        new_refresh, _ = generate_and_store_refresh(user)
        new_access = generate_access_token(user)
        response = Response({"new_access_token": new_access}, status=200)
        return _set_refresh_cookie(response, new_refresh)

# -------- Admin --------
class AdminUserListView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=["Admin"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
            OpenApiParameter("q", str, required=False),
        ],
        responses={200: UserSerializer(many=True)},
        description="Lista usuarios (ADMIN). Buscar por ?q= (id/email/name)."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        q = request.query_params.get("q")
        qs = User.objects.all().order_by("id")
        if q:
            qs = qs.filter(Q(id__icontains=q) | Q(email__icontains=q) | Q(name__icontains=q))
        return Response(UserSerializer(paginated(qs, offset, limit), many=True).data)

class AdminUserDetailView(APIView):
    permission_classes = [IsAdmin]
    @extend_schema(tags=["Admin"], responses={200: UserSerializer})
    def get(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail":"No existe"}, status=404)
        return Response(UserSerializer(user).data)

class AdminUserUpdateView(APIView):
    permission_classes = [IsAdmin]
    @extend_schema(tags=["Admin"], request=AdminUserUpdateSerializer, responses={200: UserSerializer})
    def put(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail": "No existe"}, status=404)

        ser = AdminUserUpdateSerializer(instance=user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)   # <- aquí se valida unicidad y otros
        ser.save()
        return Response(UserSerializer(user).data)
class AdminUserDeleteView(APIView):
    permission_classes = [IsAdmin]
    @extend_schema(tags=["Admin"], request=None, responses={204: None})
    def delete(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"detail":"No existe"}, status=404)
        user.delete()  # cascada a educator/publications/commentaries/subscriptions
        return Response({"detail":"eliminated"}, status=204)

class AdminPublicationUpdateView(APIView):
    permission_classes = [IsAdmin]
    @extend_schema(tags=["Admin"], request=PublicationUpdateSerializer, responses={200: PublicationSerializer})
    def put(self, request, pub_id):
        ser = PublicationUpdateSerializer(data=request.data)
        ser.is_valid()
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        pub = Publication.objects.filter(id=pub_id).first()
        if not pub:
            return Response({"detail":"No existe"}, status=404)
        if "title" in request.data: pub.title = request.data["title"]
        if "publication_type" in request.data: pub.publication_type = request.data["publication_type"]
        if "content" in request.data:
            content_url = pub.content_url
            updated = update_publication_html(content_url, request.data["content"])
            if updated != "ok":
                return Response({"detail": updated }, status=500)
        pub.save()
        return Response(PublicationSerializer(pub).data)

class AdminPublicationDeleteView(APIView):
    permission_classes = [IsAdmin]
    @extend_schema(tags=["Admin"], request=None, responses={204: None})
    def delete(self, request, pub_id):
        pub = Publication.objects.filter(id=pub_id).first()
        if not pub:
            return Response({"detail":"No existe"}, status=404)
        pub.delete()  # cascada a comentarios
        return Response(status=204)

# -------- Me (Educator/User) --------
class MeEducatorDetailView(APIView):

    @extend_schema(tags=["Me"],
                   description="Datos del educator autenticado (incluye user y publications).",
                   responses={200: MeEducatorDetailSerializer})
    def get(self, request):
        edu = getattr(request.user, "educator", None)
        if not edu:
            return Response({"detail":"No es educator"}, status=403)
        data = EducatorSerializer(edu).data
        data["publications"] = PublicationSerializer(edu.publications.all(), many=True).data
        return Response(data)

class MeEducatorUpdateView(APIView):
    @extend_schema(
        tags=["Me"],
        request=EducatorProfileSerializer,
        responses={200: EducatorProfileSerializer},
        description="Actualiza el perfil completo del educador autenticado."
    )
    def put(self, request):
        user = request.user
        edu = getattr(user, "educator", None)
        if not edu:
            return Response({"detail": "No es educator"}, status=403)
        
        ser = EducatorProfileSerializer(instance=edu, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(EducatorProfileSerializer(edu).data, status=200)

    @extend_schema(request=EducatorProfileSerializer, responses={200: EducatorProfileSerializer})
    def patch(self, request):
        return self.put(request)

class MeDeleteView(APIView):

    @extend_schema(
        tags=["Me"],
        request=DeleteMeSerializer,
        responses={204: None},
        description="Borrar cuenta del usuario autenticado. Requiere password."
    )
    def put(self, request):
        pwd = request.data.get("password")
        if not pwd or not check_password(pwd, request.user.password):
            return Response({"detail":"Password inválido"}, status=401)
        request.user.delete()
        return Response(status=204)

# -------- Educator list & search --------
class EducatorListView(APIView):

    @extend_schema(
        tags=["Educators"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: EducatorWithFollowSerializer(many=True)},
        description="Lista de educators con paginación obligatoria. Incluye flags de relación con el usuario autenticado."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        qs = Educator.objects.select_related("user").order_by("id")
        page_qs = list(paginated(qs, offset, limit))

        me_edu = get_me_educator(request)

        # Por defecto, todos false
        followed_by_me_ids = set()
        following_me_ids = set()

        if me_edu:
            # Yo sigo a estos (subscriber=yo, subscribed=ellos)
            subs_i_follow = Subscription.objects.filter(
                subscriber=me_edu,
                subscribed__in=page_qs,
            ).values_list("subscribed_id", flat=True)
            followed_by_me_ids = set(subs_i_follow)

            # Ellos me siguen (subscriber=ellos, subscribed=yo)
            subs_follow_me = Subscription.objects.filter(
                subscriber__in=page_qs,
                subscribed=me_edu,
            ).values_list("subscriber_id", flat=True)
            following_me_ids = set(subs_follow_me)

        results = []
        for edu in page_qs:
            item = EducatorSerializer(edu).data
            item["followed_by_me"] = edu.id in followed_by_me_ids
            item["following_me"] = edu.id in following_me_ids
            results.append(item)

        return Response(results, status=200)

class EducatorSearchView(APIView):

    @extend_schema(
        tags=["Educators"],
        parameters=[
            OpenApiParameter("q", str, required=True, default="nickname incompl"),
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: EducatorWithFollowSerializer(many=True)},
        description="Busca educators por parecido de nickname. Incluye flags de relación con el usuario autenticado."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        q = request.query_params.get("q", "").strip()
        if not q:
            return Response({"detail": "Parámetro q requerido"}, status=400)

        qs = Educator.objects.filter(nick_name__icontains=q).select_related("user").order_by("id")
        page_qs = list(paginated(qs, offset, limit))

        me_edu = get_me_educator(request)

        followed_by_me_ids = set()
        following_me_ids = set()

        if me_edu:
            subs_i_follow = Subscription.objects.filter(
                subscriber=me_edu,
                subscribed__in=page_qs,
            ).values_list("subscribed_id", flat=True)
            followed_by_me_ids = set(subs_i_follow)

            subs_follow_me = Subscription.objects.filter(
                subscriber__in=page_qs,
                subscribed=me_edu,
            ).values_list("subscriber_id", flat=True)
            following_me_ids = set(subs_follow_me)

        results = []
        for edu in page_qs:
            item = EducatorSerializer(edu).data
            item["followed_by_me"] = edu.id in followed_by_me_ids
            item["following_me"] = edu.id in following_me_ids
            results.append(item)

        return Response(results, status=200)

class EducatorDetailView(APIView):

    @extend_schema(
        tags=["Educators"],
        responses={200: EducatorDetailWithPublicationsSerializer, 404: MessageSerializer},
        description=(
            "Detalle de un educator por ID. Incluye user, publications y flags "
            "followed_by_me / following_me respecto al usuario autenticado."
        )
    )
    def get(self, request, educator_id: int):
        edu = (
            Educator.objects
            .select_related("user")
            .filter(id=educator_id)
            .first()
        )
        if not edu:
            return Response({"detail": "Educator no encontrado."}, status=404)

        me_edu = get_me_educator(request)

        followed_by_me = False
        following_me = False

        if me_edu:
            # Yo sigo a este educator
            followed_by_me = Subscription.objects.filter(
                subscriber=me_edu,
                subscribed=edu,
            ).exists()

            # Este educator me sigue a mí
            following_me = Subscription.objects.filter(
                subscriber=edu,
                subscribed=me_edu,
            ).exists()

        data = EducatorSerializer(edu).data
        data["publications"] = PublicationSerializer(
            edu.publications.select_related("category").all().order_by("-created_at"),
            many=True
        ).data
        data["followed_by_me"] = followed_by_me
        data["following_me"] = following_me

        return Response(data, status=200)

# -------- Categories --------
class CategoryListView(APIView):

    @extend_schema(
        tags=["Categories"],
        responses={200: CategorySerializer(many=True)},
        description="Lista todas las categorías disponibles para publicaciones."
    )
    def get(self, request):
        categories = Category.objects.all()
        return Response(CategorySerializer(categories, many=True).data)

# -------- Publications --------
class PublicationListView(APIView):

    @extend_schema(
        tags=["Publications"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
            OpenApiParameter("category_id", int, required=False),
        ],
        responses={200: PublicationSerializer(many=True)},
        description="Todas las publicaciones. Filtrar opcionalmente por category_id."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        qs = Publication.objects.select_related("educator", "educator__user", "category").order_by("-created_at")
        category_id = request.query_params.get("category_id")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data)

# -------- Feed de Publicaciones (Anti-N+1) --------
class PublicationFeedView(APIView):
    @extend_schema(
        tags=["Publications"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: PublicationSerializer(many=True)},
        description="Feed unificado de publicaciones de los educadores que el usuario sigue."
    )
    def get(self, request):
        me_edu = get_me_educator(request)
        if not me_edu:
            return Response([], status=200)

        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        following_ids = Subscription.objects.filter(subscriber=me_edu).values_list("subscribed_id", flat=True)
        qs = (
            Publication.objects
            .filter(educator_id__in=following_ids)
            .select_related("educator", "educator__user", "category")
            .order_by("-created_at")
        )
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data, status=200)

# -------- Publication by ID --------
class PublicationDetailView(APIView):

    @extend_schema(
        tags=["Publications"],
        responses={200: PublicationSerializer, 404: MessageSerializer},
        description="Obtiene la publicación por ID, incluyendo comentarios y el contenido HTML."
    )
    def get(self, request, publication_id: int):
        pub = (
            Publication.objects
            .select_related("educator", "educator__user", "category")
            .filter(id=publication_id)
            .first()
        )
        if not pub:
            return Response({"detail": "Publicación no encontrada."}, status=404)

        data = PublicationSerializer(pub).data

        comments = (
            Commentary.objects
            .select_related("educator", "educator__user")
            .filter(publication=pub)
            .order_by("-created_at")
        )

        data["comments"] = CommentarySerializer(comments, many=True).data
        
        try:
            content_html = get_publication_html(pub.content_url)
        except Exception as e:
            return Response({"detail": f"Error al leer el contenido."}, status=400)

        data["content"] = content_html

        return Response(data, status=200)

class PublicationByUserView(APIView):
    @extend_schema(
        tags=["Publications"],
        parameters=[OpenApiParameter("offset", int, required=True), OpenApiParameter("limit", int, required=True)],
        responses={200: PublicationSerializer(many=True)}
    )
    def get(self, request, user_id):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        edu = Educator.objects.filter(user_id=user_id).first()
        if not edu:
            return Response({"detail":"User sin educator"}, status=404)
        qs = Publication.objects.select_related("educator", "educator__user", "category").filter(educator=edu).order_by("-created_at")
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data)

class PublicationMeListView(APIView):

    @extend_schema(tags=["Publications (Me)"], parameters=[OpenApiParameter("offset", int, required=True), OpenApiParameter("limit", int, required=True)], responses={200: PublicationSerializer(many=True)})
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        edu = request.user.educator
        qs = Publication.objects.select_related("educator", "educator__user", "category").filter(educator=edu).order_by("-created_at")
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data)

class PublicationMeCreateView(APIView):

    @extend_schema(
        tags=["Publications (Me)"],
        request=PublicationCreateSerializer,
        responses={201: PublicationSerializer},
        description="Tipo de contenido son ARTICLE/FORUM. Crea publicación del educator autenticado. Guarda content como .html en /media."
    )
    def post(self, request):
        edu = request.user.educator
        ser = PublicationCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        content_url = save_publication_html(ser.validated_data["content"])
        category_id = ser.validated_data.get("category_id")
        category = None
        if category_id:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return Response({"detail": "Categoría no encontrada."}, status=400)
        pub = Publication.objects.create(
            title=ser.validated_data["title"],
            publication_type=ser.validated_data["publication_type"],
            content_url=content_url,
            educator=edu,
            category=category
        )
        return Response(PublicationSerializer(pub).data, status=201)

class PublicationMeUpdateView(APIView):

    @extend_schema(tags=["Publications (Me)"], request=PublicationUpdateSerializer, responses={200: PublicationSerializer})
    def put(self, request, publication_id):
        ser = PublicationUpdateSerializer(data=request.data)
        ser.is_valid()
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        edu = request.user.educator
        pub = Publication.objects.filter(id=publication_id, educator=edu).first()
        if not pub:
            return Response({"detail":"No existe o no es tuya"}, status=404)
        if "title" in request.data: pub.title = request.data["title"]
        if "publication_type" in request.data: pub.publication_type = request.data["publication_type"]
        if "content" in request.data:
            content_url = pub.content_url
            updated = update_publication_html(content_url, request.data["content"])
            if updated != "ok":
                return Response({"detail": updated }, status=500)
        if "category_id" in request.data:
            cid = request.data["category_id"]
            if cid is None:
                pub.category = None
            else:
                cat = Category.objects.filter(id=cid).first()
                if not cat:
                    return Response({"detail": "Categoría no encontrada."}, status=400)
                pub.category = cat
        pub.save()
        pub.refresh_from_db()
        return Response(PublicationSerializer(pub).data)

class PublicationMeDeleteView(APIView):

    @extend_schema(tags=["Publications (Me)"], request=None, responses={204: None})
    def delete(self, request, publication_id):
        edu = request.user.educator
        pub = Publication.objects.filter(id=publication_id, educator=edu).first()
        if not pub:
            return Response({"detail":"No existe o no es tuya"}, status=404)
        pub.delete()
        return Response(status=204)

class PublicationSearchView(APIView):

    @extend_schema(
        tags=["Publications"],
        parameters=[
            OpenApiParameter("nickname_part", str, required=False),
            OpenApiParameter("title_part", str, required=False),
            OpenApiParameter("category_id", int, required=False),
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: PublicationSerializer(many=True)},
        description="Busca por nickname, title y/o category_id. Requiere al menos uno de los tres."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        nick = request.query_params.get("nickname_part", "").strip()
        title = request.query_params.get("title_part", "").strip()
        category_id = request.query_params.get("category_id", "").strip()
        if not nick and not title and not category_id:
            return Response({"detail": "Se requiere nickname_part, title_part o category_id"}, status=400)
        qs = Publication.objects.select_related("educator", "educator__user", "category")
        if nick:
            qs = qs.filter(educator__nick_name__icontains=nick)
        if title:
            qs = qs.filter(title__icontains=title)
        if category_id:
            qs = qs.filter(category_id=category_id)
        qs = qs.order_by("-created_at")
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data)

# -------- Commentary (me) --------
class CommentaryMeCreateView(APIView):

    @extend_schema(tags=["Commentary (Me)"], request=CommentaryCreateSerializer, responses={201: CommentarySerializer})
    def post(self, request, publication_id):
        edu = request.user.educator
        pub = Publication.objects.filter(id=publication_id).first()
        if not pub: return Response({"detail":"Publicación no existe"}, status=404)
        ser = CommentaryCreateSerializer(data=request.data)
        if not ser.is_valid(): return Response(ser.errors, status=400)
        com = Commentary.objects.create(content=ser.validated_data["content"], educator=edu, publication=pub)
        return Response(CommentarySerializer(com).data, status=201)

class CommentaryMeUpdateView(APIView):

    @extend_schema(tags=["Commentary (Me)"], request=CommentaryUpdateSerializer, responses={200: CommentarySerializer})
    def put(self, request, commentary_id):
        edu = request.user.educator
        com = Commentary.objects.filter(id=commentary_id, educator=edu).first()
        if not com: return Response({"detail":"No existe o no es tuyo"}, status=404)
        if "content" in request.data: com.content = request.data["content"]
        com.save()
        return Response(CommentarySerializer(com).data)

class CommentaryMeDeleteView(APIView):

    @extend_schema(tags=["Commentary (Me)"], request=None, responses={204: None})
    def delete(self, request, commentary_id):
        edu = request.user.educator
        com = Commentary.objects.filter(id=commentary_id, educator=edu).first()
        if not com: return Response({"detail":"No existe o no es tuyo"}, status=404)
        com.delete()
        return Response(status=204)

# -------- Subscriptions --------
class FollowView(APIView):

    @extend_schema(tags=["Subscription"], request=None, responses={200: MessageSerializer})
    def post(self, request, subscribed_id):
        me = request.user.educator
        if me.id == subscribed_id:
            return Response({"detail":"No puedes seguirte a ti mismo"}, status=400)
        target = Educator.objects.filter(id=subscribed_id).first()
        if not target: return Response({"detail":"Educator no existe"}, status=404)
        Subscription.objects.get_or_create(subscriber=me, subscribed=target)
        return Response({"detail":"OK"}, status=200)

class UnfollowView(APIView):

    @extend_schema(tags=["Subscription"], request=None, responses={200: MessageSerializer })
    def post(self, request, subscribed_id):
        me = request.user.educator
        target = Educator.objects.filter(id=subscribed_id).first()
        if not target: return Response({"detail":"Educator no existe"}, status=404)
        Subscription.objects.filter(subscriber=me, subscribed=target).delete()
        return Response({"detail":"OK"}, status=200)

class FollowersMeListView(APIView):

    @extend_schema(
        tags=["Subscription"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: EducatorSerializer(many=True)},
        description="Lista de educators que SIGUEN al usuario autenticado."
    )
    def get(self, request):
        edu = request.user.educator

        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        # Subscriptions donde YO soy el 'subscribed' (me siguen)
        subs_qs = (
            Subscription.objects
            .filter(subscribed=edu)
            .select_related("subscriber", "subscriber__user")
            .order_by("id")
        )

        subs_page = paginated(subs_qs, offset, limit)
        followers = [s.subscriber for s in subs_page]

        return Response(EducatorSerializer(followers, many=True).data, status=200)

class FollowingMeListView(APIView):

    @extend_schema(
        tags=["Subscription"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: EducatorSerializer(many=True)},
        description="Lista de educators a los que el usuario autenticado SIGUE."
    )
    def get(self, request):
        edu = request.user.educator

        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        # Subscriptions donde YO soy el 'subscriber' (yo sigo a otros)
        subs_qs = (
            Subscription.objects
            .filter(subscriber=edu)
            .select_related("subscribed", "subscribed__user")
            .order_by("id")
        )

        subs_page = paginated(subs_qs, offset, limit)
        following = [s.subscribed for s in subs_page]

        return Response(EducatorSerializer(following, many=True).data, status=200)

class FollowersByEducatorView(APIView):

    @extend_schema(
        tags=["Subscription"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: EducatorSerializer(many=True), 404: MessageSerializer},
        description="Lista de educators que SIGUEN a un educator dado (por ID)."
    )
    def get(self, request, educator_id: int):
        # Verificar que el educator exista
        target = Educator.objects.select_related("user").filter(id=educator_id).first()
        if not target:
            return Response({"detail": "Educator no encontrado."}, status=404)

        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        subs_qs = (
            Subscription.objects
            .filter(subscribed=target)
            .select_related("subscriber", "subscriber__user")
            .order_by("id")
        )

        subs_page = paginated(subs_qs, offset, limit)
        followers = [s.subscriber for s in subs_page]

        return Response(EducatorSerializer(followers, many=True).data, status=200)

class FollowingByEducatorView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Subscription"],
        parameters=[
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: EducatorSerializer(many=True), 404: MessageSerializer},
        description="Lista de educators a los que un educator dado SIGUE (por ID)."
    )
    def get(self, request, educator_id: int):
        # Verificar que el educator exista
        source = Educator.objects.select_related("user").filter(id=educator_id).first()
        if not source:
            return Response({"detail": "Educator no encontrado."}, status=404)

        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        subs_qs = (
            Subscription.objects
            .filter(subscriber=source)
            .select_related("subscribed", "subscribed__user")
            .order_by("id")
        )

        subs_page = paginated(subs_qs, offset, limit)
        following = [s.subscribed for s in subs_page]

        return Response(EducatorSerializer(following, many=True).data, status=200)


class ImageUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        description="Upload an image for a publication",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "publication_id": {"type": "integer"},
                    "file": {
                        "type": "string",
                        "format": "binary"
                    },
                },
                "required": ["publication_id", "file"],
            }
        },
        responses=ImageSerializer,
    )
    def post(self, request):
        serializer = ImageUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        publication_id = serializer.validated_data["publication_id"]
        file = serializer.validated_data["file"]

        if file.size > settings.MAX_UPLOAD_SIZE:
            return Response({"detail": "La imagen supera el tamaño máximo permitido."}, status=413)

        publication = Publication.objects.filter(pk=publication_id).first()
        if publication is None:
            return Response({"detail": "Publicación no encontrada."}, status=404)
        educator = getattr(request.user, "educator", None)
        is_admin = getattr(request.user, "role", None) == Role.ADMIN or getattr(request.user, "is_staff", False)
        if not is_admin and (educator is None or publication.educator_id != educator.id):
            return Response({"detail": "No tienes permiso para agregar imágenes a esta publicación."}, status=403)

        image = Image.objects.create(publication=publication, file=file)

        return Response(ImageSerializer(image).data, status=status.HTTP_201_CREATED)


class ChatView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "chat"

    @extend_schema(
        summary="Chat con Asistente Virtual Google Gemini",
        description="Permite enviar consultas pedagógicas al Tutor IA Gemini con contexto opcional de una publicación.",
        request=AIChatRequestSerializer,
        responses={200: AIChatResponseSerializer, 400: dict, 500: dict},
        tags=["AI Assistant"]
    )
    def post(self, request):
        message_text = request.data.get("message", "")
        history_items = request.data.get("history", request.data.get("messages", []))
        if not isinstance(message_text, str) or len(message_text) > 4000:
            return Response({"detail": "El mensaje debe tener como máximo 4000 caracteres."}, status=400)
        if history_items is not None and (not isinstance(history_items, list) or len(history_items) > 20):
            return Response({"detail": "El historial debe contener como máximo 20 mensajes."}, status=400)
        if isinstance(history_items, list) and any(
            not isinstance(item, dict) or not isinstance(item.get("content", ""), str) or len(item.get("content", "")) > 4000
            for item in history_items
        ):
            return Response({"detail": "Cada mensaje del historial debe ser texto de hasta 4000 caracteres."}, status=400)

        serializer = AIChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            # Soporte de formato legacy {'messages': [...], 'publication_id': ...}
            messages = request.data.get("messages", [])
            publication_id = request.data.get("publication_id") or request.data.get("publicationId")
            
            if messages and isinstance(messages, list):
                last_msg = messages[-1].get("content", "") if len(messages) > 0 else ""
                history = messages[:-1]
                res = generate_chat_response(message=last_msg, publication_id=publication_id, history=history)
                return Response({
                    "response": res["response"],
                    "context_used": res["context_used"],
                    "reply": res["response"]
                }, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        message = serializer.validated_data["message"]
        publication_id = serializer.validated_data.get("publication_id")
        history = serializer.validated_data.get("history", [])

        res = generate_chat_response(message=message, publication_id=publication_id, history=history)

        return Response({
            "response": res["response"],
            "context_used": res["context_used"],
            "reply": res["response"]
        }, status=status.HTTP_200_OK)
