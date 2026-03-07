from django.urls import path
from .views import (
    AuthLoginView, AuthSignupView, AuthLogoutView, AuthRefreshView,
    AdminUserListView, AdminUserDetailView, AdminUserUpdateView, AdminUserDeleteView,
    AdminPublicationUpdateView, AdminPublicationDeleteView,
    MeDeleteView, MeEducatorDetailView, MeEducatorUpdateView,
    EducatorListView, EducatorSearchView, EducatorDetailView,
    PublicationListView, PublicationByUserView, PublicationMeListView, PublicationDetailView,
    PublicationMeCreateView, PublicationMeUpdateView, PublicationMeDeleteView,
    PublicationSearchView,
    CommentaryMeCreateView, CommentaryMeUpdateView, CommentaryMeDeleteView,
    FollowView, UnfollowView, FollowersMeListView, FollowingMeListView, FollowersByEducatorView, FollowingByEducatorView,
    ImageUploadView
)

urlpatterns = [
    # Auth
    path("auth/login", AuthLoginView.as_view()),
    path("auth/signup", AuthSignupView.as_view()),
    path("auth/logout", AuthLogoutView.as_view()),
    path("auth/refresh", AuthRefreshView.as_view()),

    # Admin
    path("admin/users", AdminUserListView.as_view()),
    path("admin/users/<int:user_id>", AdminUserDetailView.as_view()),
    path("admin/users/<int:user_id>/update", AdminUserUpdateView.as_view()),
    path("admin/users/<int:user_id>/delete", AdminUserDeleteView.as_view()),
    path("admin/publications/<int:pub_id>/update", AdminPublicationUpdateView.as_view()),
    path("admin/publications/<int:pub_id>/delete", AdminPublicationDeleteView.as_view()),

    # Me (User/Educator)
    path("educator/me", MeEducatorDetailView.as_view()),              # GET datos personales (incluye user/publications)
    path("educator/me/update", MeEducatorUpdateView.as_view()),       # PUT actualizar perfil
    path("educator/me/delete", MeDeleteView.as_view()),               # DELETE: borrar cuenta autenticada (req body: password)

    # Educators
    path("educator", EducatorListView.as_view()),                     # GET con offset & limit
    path("educator/search", EducatorSearchView.as_view()),            # GET ?q=nickpart&offset=&limit=
    path("educators/<int:educator_id>", EducatorDetailView.as_view(), name="educator-detail"),

    # Publications
    path("publications/<int:publication_id>", PublicationDetailView.as_view(), name="publication-detail"),
    path("publication", PublicationListView.as_view()),               # GET todas (offset/limit)
    path("publication/by-user/<int:user_id>", PublicationByUserView.as_view()),
    path("publication/me", PublicationMeListView.as_view()),          # GET
    path("publication/me/create", PublicationMeCreateView.as_view()), # POST
    path("publication/me/update/<int:publication_id>", PublicationMeUpdateView.as_view()), # PUT
    path("publication/me/<int:publication_id>", PublicationMeDeleteView.as_view()),        # DELETE
    path("publication/search", PublicationSearchView.as_view()),      # GET ?nickname_part=&title=&offset=&limit=

    # Commentary (me)
    path("commentary/me/<int:publication_id>", CommentaryMeCreateView.as_view()),         # POST
    path("commentary/me/update/<int:commentary_id>", CommentaryMeUpdateView.as_view()),   # PUT
    path("commentary/me/delete/<int:commentary_id>", CommentaryMeDeleteView.as_view()),          # DELETE

    # Subscription
    path("subscription/follow/<int:subscribed_id>", FollowView.as_view()),
    path("subscription/unfollow/<int:subscribed_id>", UnfollowView.as_view()),
    path("subscription/me/followers", FollowersMeListView.as_view(), name="me-followers"),
    path("subscription/me/following", FollowingMeListView.as_view(), name="me-following"),
    path("subscription/<int:educator_id>/followers", FollowersByEducatorView.as_view(), name="educator-followers"),
    path("subscription/<int:educator_id>/following", FollowingByEducatorView.as_view(), name="educator-following"),
    
    #Image
    path("upload/", ImageUploadView.as_view(), name="image-upload"),
]
