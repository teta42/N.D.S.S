from django.shortcuts import render
import json
from django.http import JsonResponse
from service_accounts.models import CustomUser
from django.contrib.auth import login, authenticate, logout
from datetime import datetime, timedelta

def registration(request):
    if request.method == 'GET':
        return render(request, 'reg.html')
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('login')
            email = data.get('email')
            password = data.get('password')
            remember_me = data.get('rememberMe', False)

            if CustomUser.objects.filter(username=username).exists():
                return JsonResponse({"status": "login_not_unique"}, status=400)
            
            user = CustomUser.objects.create_user(username=username, email=email, password=password)
            
            login(request, user)

            request.session.set_expiry(0 if not remember_me else None)

            return JsonResponse({"status": "ok"}, status=200)
        
        except json.JSONDecodeError:
            print("error invalid_json")
            return JsonResponse({"error": "invalid_json"}, status=400)
        except Exception as e:
            print(f"error {str(e)}")
            return JsonResponse({"error": "error"}, status=500)

    return JsonResponse({"error": "method_not_allowed"}, status=405)

def authorization(request):
    if request.method == 'GET':
        return render(request, 'aut.html')

    elif request.method == 'POST':
        try:
            # Получаем данные из тела запроса
            request_data = json.loads(request.body)
            username = request_data.get('login')
            password = request_data.get('password')
            remember_user = request_data.get('rememberMe', False)
            
            #region
            user = CustomUser.objects.filter(username=username).first() # Получаем первого пользователя
            if not user:
                return JsonResponse({"error": "no_such_account_exists"}, status=404)

            pb = user.pb

            if datetime.now() <= pb.unlock_date: # Проверяем блокеровку 
                return JsonResponse({"error": "account_blocked", "unlocked": str(pb.unlock_date - datetime.now())}, status=403)

            if user.check_password(password):
                login(request, user)
                request.session.set_expiry(0 if not remember_user else None) # Запоменать пользователя или нет
                return JsonResponse({"status": "ok"}, status=200)
            
            else:
                pb.incorrect_password_counter += 1
                # Блокируем аккаунт
                if pb.incorrect_password_counter >= 4: # переводим часы в объект времени
                    pb.unlock_date = datetime.now() + timedelta(hours=pb.next_blocking_for_how_long)
                    pb.incorrect_password_counter = 0
                    pb.save()
                    return JsonResponse({"error": "account_blocked", "unlocked": str(pb.unlock_date - datetime.now())}, status=403)
                pb.save()
                return JsonResponse({"error": "wrong_password"}, status=401)
            #endregion

        except json.JSONDecodeError:
            print("error invalid_json")
            return JsonResponse({"error": "invalid_json"}, status=401)
        except Exception as e:
            print(f"error {str(e)}")
            return JsonResponse({"error": "error"}, status=500)
        
    return JsonResponse({"error": "method_not_allowed"}, status=405)

def change(request):
    if request.method == 'GET':
        return render(request, 'cha.html')
    elif request.method == 'PUT':
        data = json.loads(request.body)
        password = data.get('password')
        username = data.get('login')
        
        user = CustomUser.objects.get(pk=request.user.user_id)
        
        if password is not None:
            user.set_password(password)
        if username is not None:
            user.username = username
            
        user.save()
        login(request, user)
        
        return JsonResponse({"status": "fully completed"}, status=200)
    
    return JsonResponse({"error": "method_not_allowed"}, status=405)

def delete(request):
    if request.user.is_authenticated:
        user = CustomUser.objects.get(pk=request.user.user_id)
        user.delete()
        return JsonResponse({"status": "fully completed"}, status=200)
    
    return JsonResponse({"error": "you are a shapeshifter"}, status=401)

def out(request):
    if request.user.is_authenticated:
        logout(request=request)
        return JsonResponse({"status": "fully completed"}, status=200)
    
    return JsonResponse({"error": "you are a shapeshifter"}, status=401)