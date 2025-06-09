from rest_framework import routers
from .views import NoteAPI
from django.urls import path, include
from .views import RegView, LoginView

router = routers.DefaultRouter()
router.register(r'notes', NoteAPI, basename='notes')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegView.as_view(), name='reg'),
    path('login/', LoginView.as_view(), name='login')
]