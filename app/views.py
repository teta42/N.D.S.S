from rest_framework import viewsets
from rest_framework.views import APIView
from .models import Note
from .serializer import NoteSerializer, RegSeri, LoginSer
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login

class NoteAPI(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Note.objects.filter(user=self.request.user)
        else:
            return Note.objects.none()  # Возвращает пустой queryset
        
class RegView(APIView):
    def post(self, request):
        ser = RegSeri(data=request.data)
        
        if ser.is_valid():
            user = ser.save()
            login(request, user)
            return Response({'message': 'User created successfully'}, status=status.HTTP_201_CREATED)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            return Response({'message': 'Login successful'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)