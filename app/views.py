from rest_framework import viewsets
from .models import Note
from .serializer import NoteSerializer

class NoteAPI(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    queryset = Note.objects.all()