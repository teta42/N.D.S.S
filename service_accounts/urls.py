from django.urls import path
from service_accounts import views

urlpatterns = [
    path('registration/', views.registration, name='reg'),
    path('authorization/', views.authorization, name='aut'),
    path('change/', views.change, name='change'),
    path('logout/', views.out, name='logout'),
    path('delete/', views.delete, name='del')
]
