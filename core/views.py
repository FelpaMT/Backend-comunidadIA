from django.db.models import Q, F
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiRequest
from .models import User, Educator, Publication, Commentary, Subscription, Role, PublicationType, RefreshToken, Image
# Arriba en views.py (importa los nuevos serializers)
from .serializers import (
    UserSerializer, UserCreateSerializer, EducatorSerializer, MeEducatorDetailSerializer, EducatorWithFollowSerializer, EducatorDetailWithPublicationsSerializer,
    PublicationSerializer, PublicationCreateSerializer,
    CommentarySerializer, CommentaryCreateSerializer,
    SubscriptionSerializer,
    LoginSerializer, RefreshTokenSerializer, DeleteMeSerializer,
    AdminUserUpdateSerializer,
    PublicationUpdateSerializer, CommentaryUpdateSerializer,
    MessageSerializer,
    TokenPairSerializer,
    RefreshResponseSerializer,
    EducatorUserUpdateSerializer,
    ImageUploadRequestSerializer, ImageSerializer
)
from .permissions import IsAdmin, IsOwnerEducatorObject
from .jwt_utils import generate_access_token, generate_and_store_refresh, decode_any_token, invalidate_refresh, new_access_from_access
from .storage import save_publication_html, update_publication_html, get_publication_html
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
class AuthSignupView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=UserCreateSerializer,
        responses={201: UserSerializer},
        examples=[
            OpenApiExample("Signup req", value={"email":"john@doe.com","name":"John","password":"Secret123","role":"EDUCATOR", "nick_name": "johnny"}),
            OpenApiExample("Signup res", value={"id":1,"name":"John","email":"john@doe.com","role":"EDUCATOR"}),
        ],
        description="Crea usuario (solo role EDUCATOR permitido aquí)."
    )
    def post(self, request):
        data = request.data.copy()
        if data.get("role") == "ADMIN":
            return Response({"detail":"No se puede crear ADMIN aquí."}, status=400)

        ser = UserCreateSerializer(data=data)
        if ser.is_valid():
            user = ser.save()
            access = generate_access_token(user)
            refresh, _ = generate_and_store_refresh(user)
            return Response({"user": UserSerializer(user).data, "access_token": access, "refresh_token": refresh}, status=201)
        return Response(ser.errors, status=400)

class AuthLoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=LoginSerializer,  # 👈 ahora Swagger muestra el body
        responses={200: TokenPairSerializer},
        description="Login con email y password."
    )
    def post(self, request):
        email = request.data.get("email")
        pwd = request.data.get("password")
        user = User.objects.filter(email=email).first()
        if not user or not check_password(pwd, user.password):
            return Response({"detail":"Credenciales inválidas"}, status=401)
        access = generate_access_token(user)
        refresh, _ = generate_and_store_refresh(user)
        return Response({"access_token": access, "refresh_token": refresh}, status=200)

class AuthLogoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=RefreshTokenSerializer,
        responses={200: MessageSerializer},
        description="Elimina el refresh token en DB para invalidar sesiones."
    )
    def post(self, request):
        token = request.data.get("refresh_token")
        if not token:
            return Response({"detail": "refresh_token requerido"}, status=400)

        ref = RefreshToken.objects.filter(token=token).first()
        if ref:
            ref.delete()
        return Response({"detail": "OK"}, status=200)

class AuthRefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        request=RefreshTokenSerializer,
        responses={200: RefreshResponseSerializer},
        description="Recibe access_token y retorna uno nuevo (usa refresh guardado en DB)."
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response({"detail": "refresh_token requerido"}, status=400)

        ref = RefreshToken.objects.filter(token=refresh_token).first()
        if not ref:
            return Response({"detail": "Refresh token inválido"}, status=401)
        if ref.expiry_date < timezone.now():
            return Response({"detail": "Refresh token expirado"}, status=401)

        user = ref.user
        new_access = generate_access_token(user)
        return Response({"new_access_token": new_access}, status=200)

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
        request=EducatorUserUpdateSerializer,
        responses={200: MeEducatorDetailSerializer},
        description="Actualizar datos de user (name,email) y educator (nick_name)."
    )
    def put(self, request):
        user = request.user
        edu = getattr(user, "educator", None)
        if not edu:
            return Response({"detail":"No es educator"}, status=403)
        # user
        ser = EducatorUserUpdateSerializer(data=request.data)
        ser.is_valid()
        if not ser.is_valid():
            return Response(ser.errors, status=400)
        for f in ["name","email"]:
            if f in request.data:
                setattr(user, f, request.data[f])
        user.save()
        # educator
        if "nick_name" in request.data:
            edu.nick_name = request.data["nick_name"]
            edu.save()
        return Response(EducatorSerializer(edu).data)

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
            edu.publications.all().order_by("-created_at"),
            many=True
        ).data
        data["followed_by_me"] = followed_by_me
        data["following_me"] = following_me

        return Response(data, status=200)

# -------- Publications --------
class PublicationListView(APIView):

    @extend_schema(
        tags=["Publications"],
        parameters=[OpenApiParameter("offset", int, required=True), OpenApiParameter("limit", int, required=True)],
        responses={200: PublicationSerializer(many=True)},
        description="Todas las publicaciones."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        qs = Publication.objects.select_related("educator","educator__user").order_by("-created_at")
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data)

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
            .select_related("educator", "educator__user")
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
        qs = Publication.objects.filter(educator=edu).order_by("-created_at")
        return Response(PublicationSerializer(paginated(qs, offset, limit), many=True).data)

class PublicationMeListView(APIView):

    @extend_schema(tags=["Publications (Me)"], parameters=[OpenApiParameter("offset", int, required=True), OpenApiParameter("limit", int, required=True)], responses={200: PublicationSerializer(many=True)})
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        edu = request.user.educator
        qs = Publication.objects.filter(educator=edu).order_by("-created_at")
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
        pub = Publication.objects.create(
            title=ser.validated_data["title"],
            publication_type=ser.validated_data["publication_type"],
            content_url=content_url,
            educator=edu
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
        pub.save()
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
            OpenApiParameter("offset", int, required=True),
            OpenApiParameter("limit", int, required=True),
        ],
        responses={200: PublicationSerializer(many=True)},
        description="Busca por nickname (educator) y/o title (publication). Requiere al menos uno."
    )
    def get(self, request):
        try:
            offset, limit = require_offset_limit(request)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        nick = request.query_params.get("nickname_part","").strip()
        title = request.query_params.get("title_part","").strip()
        if not nick and not title:
            return Response({"detail":"Se requiere nickname_part o title"}, status=400)
        qs = Publication.objects.select_related("educator","educator__user")
        if nick:
            qs = qs.filter(educator__nick_name__icontains=nick)
        if title:
            qs = qs.filter(title__icontains=title)
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

        publication = Publication.objects.get(pk=publication_id)

        image = Image.objects.create(publication=publication, file=file)

        return Response(ImageSerializer(image).data, status=status.HTTP_201_CREATED)