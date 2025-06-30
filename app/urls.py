from rest_framework import routers
from .views import NoteAPI
from django.urls import path, include
from .views import RegView, LoginView, LoginView, LogoutView, UpdateAccountView, DeleteAccountView
from .views import CommentList

router = routers.DefaultRouter()
router.register(r'notes', NoteAPI, basename='notes')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegView.as_view(), name='reg'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('account/update/', UpdateAccountView.as_view(), name='update_account'),
    path('account/delete/', DeleteAccountView.as_view(), name='delete_account'),
    path('notes/<str:pk>/comments/', CommentList.as_view(), name='get_comments')
]