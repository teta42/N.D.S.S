from rest_framework import routers
from .views import NoteAPI

router = routers.DefaultRouter()
router.register(r'notes', NoteAPI, basename='notes')
