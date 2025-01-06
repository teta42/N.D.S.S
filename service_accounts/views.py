from django.shortcuts import render
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from service_accounts.models import Password_Blocker
from django.contrib.auth import login, authenticate, logout
from datetime import datetime, timedelta, timezone

def registration(request):
    if request.method == 'GET':
        return render(request, 'reg.html')
    elif request.method == 'POST':
        data = json.loads(request.body)
        password = data['password']
        username = data['login']
        email = data['email']
        rememberMe = data['rememberMe']
        
        uniqueness = User.objects.filter(username=username).count()
        
        if uniqueness < 1: # Проверка уникальности "логина"
            user = User.objects.create_user(username=username, email=email, password=password) # Регестрация пользователя
            if user is not None:
                login(request, user)
                if rememberMe == False:
                    request.session.set_expiry(0)
                return JsonResponse({"status": "ok"})
            return JsonResponse({"status": "not ok"})
        else:
            return JsonResponse({"status": "login_not_unique"})

def authorization(request):
    if request.method == 'GET':
        return render(request, 'aut.html')
    elif request.method == 'POST':
        data = json.loads(request.body)
        username = data['login']
        password = data['password']
        rememberMe = data['rememberMe']
        
        user_is = User.objects.filter(username=username).count()
        
        if user_is == 1:
            user = User.objects.get(username=username)
            pb = Password_Blocker.objects.get(user=user.pk)
            if datetime.now(timezone.utc) > pb.unlock_date:
                if user.check_password(password):
                    user = authenticate(request, username=username, password=password)
                    login(request, user)
                    if rememberMe == False:
                        request.session.set_expiry(0)
                    return JsonResponse({"status": "ok"})
                else:
                    if pb.incorrect_password_counter < 4:
                        pb.incorrect_password_counter += 1
                        pb.save()
                        return JsonResponse({"status": "wrong_password"})
                    elif pb.incorrect_password_counter >= 4:
                        pb.unlock_date = datetime.now(timezone.utc) + timedelta(hours=pb.next_blocking_for_how_long)
                        pb.increase_next_lock()
                        pb.incorrect_password_counter = 0
                        pb.save()
                        return JsonResponse({"status": "account_blocked", "unlocked": f"{pb.unlock_date-datetime.now(timezone.utc)}"})
            else:
                return JsonResponse({"status": "account_blocked", "unlocked": f"{pb.unlock_date-datetime.now(timezone.utc)}"})
        else:
            return JsonResponse({"status": "no_such_account_exists"})

def change(request):
    if request.method == 'GET':
        return render(request, 'cha.html')
    elif request.method == 'PUT':
        data = json.loads(request.body)
        password = data['password']
        username = data['login']
        
        user = User.objects.get(pk=request.user.id)
        if password is not None:
            user.set_password(password)  # Соответствующий набор метода set_password
        if username is not None:
            user.username = username
        user.save()
        login(request, user)
        return JsonResponse({"status": "ok"})

def delete(request):
    if request.user.is_authenticated:
        user = User.objects.get(pk=request.user.id)
        user.delete()
        return JsonResponse({"status": "ok"})
    
    return JsonResponse({"status": "not ok"})

def out(request):
    if request.user.is_authenticated:
        logout(request=request)
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "not ok"})