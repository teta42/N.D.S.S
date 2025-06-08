from rest_framework import viewsets
from .models import Note
from .serializer import NoteSerializer

class NoteAPI(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Note.objects.filter(user=self.request.user)
        else:
            return Note.objects.none()  # Возвращает пустой queryset