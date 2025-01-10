from django.urls import path
from card_manager import views as v

urlpatterns = [
    path('create/', v.create_note),
    path('<str:note_id>/', v.read_note_html),
    path('<str:note_id>/data/', v.read_note), #TODO Заменить на нормальное название
    path('<str:note_id>/write/', v.write_note),
]