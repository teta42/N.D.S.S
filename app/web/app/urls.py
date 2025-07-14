from rest_framework import routers
from django.urls import path, include
from .views import (
    NoteAPI,
    RegView,
    LoginView,
    LogoutView,
    UpdateAccountView,
    DeleteAccountView,
    CommentList,
    RandomNote,
    SearchNote
)

router = routers.DefaultRouter()
router.register(r'notes', NoteAPI, basename='notes')

urlpatterns = [
    # Специфичные пути выше
    path('notes/search/', SearchNote.as_view(), name="search"),
    path('notes/random/', RandomNote.as_view(), name='random-note'),
    path('notes/<str:pk>/comments/', CommentList.as_view(), name='get_comments'),
    
    # Роутер в самом низу
    path('', include(router.urls)),

    # Авторизация и аккаунт
    path('register/', RegView.as_view(), name='reg'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('account/update/', UpdateAccountView.as_view(), name='update_account'),
    path('account/delete/', DeleteAccountView.as_view(), name='delete_account'),
]