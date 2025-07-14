from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import Note, CustomUser
from .models import INFINITY

from django.core.files.base import ContentFile

# Сериализатор заметок
class NoteSerializer(serializers.ModelSerializer):
    content = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Note
        fields = "__all__"
        extra_kwargs = {
            "note_id": {"read_only": True},
            "created_at": {"read_only": True},
            "dead_line": {"required": False},
            "is_public": {"required": False}
        }

    def create(self, validated_data):
        user = self.context["request"].user

        content = validated_data.pop("content")
        dead_line = validated_data.pop("dead_line", INFINITY)
        only_authorized = validated_data.pop("only_authorized", False)
        to_comment = validated_data.pop("to_comment", None)
        burn_after_read = validated_data.pop("burn_after_read", False)
        is_public = validated_data.pop("is_public", False)

        return Note.objects.create_note(
            user=user,
            content=content,
            dead_line=dead_line,
            only_authorized=only_authorized,
            to_comment=to_comment,
            burn_after_read=burn_after_read,
            is_public=is_public
        )

    def update(self, instance, validated_data):
        content = validated_data.get("content")
        if content is not None:
            filename = f"{instance.note_id}.txt"
            instance.content = ContentFile(content.encode("utf-8"), name=filename)

        instance.dead_line = validated_data.get("dead_line", instance.dead_line)
        instance.only_authorized = validated_data.get("only_authorized", instance.only_authorized)
        instance.to_comment = validated_data.get("to_comment", instance.to_comment)
        instance.burn_after_read = validated_data.get("burn_after_read", instance.burn_after_read)
        instance.is_public = validated_data.get("is_public", instance.is_public)

        instance.save()
        return instance

    def to_representation(self, instance):
        """Возвращаем content как строку, через метод модели"""
        rep = super().to_representation(instance)
        rep["content"] = instance.get_content_text
        return rep



# Регистрация пользователя
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["username", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    # def validate_username(self, value):
    #     if CustomUser.objects.filter(username=value).exists():
    #         raise serializers.ValidationError("Это имя пользователя уже занято.")
    #     return value

    def create(self, validated_data):
        return CustomUser.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
        )


# Авторизация пользователя
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        user = authenticate(username=username, password=password)

        if not user or not user.is_active:
            raise serializers.ValidationError("Неверные учётные данные.")

        data["user"] = user  # Сохраняем пользователя в данных
        return data


# Обновление данных пользователя
class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = ["username", "password"]

    def validate_username(self, value):
        current_user = self.instance  # Текущий пользователь

        # Если имя не изменилось — просто возвращаем
        if current_user and current_user.username == value:
            return value

        # Проверяем, занято ли новое имя
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Это имя пользователя уже занято.")
        return value

    def update(self, instance, validated_data):
        # Обновляем только те поля, которые присутствуют в validated_data
        if "username" in validated_data:
            instance.username = validated_data["username"]

        if "password" in validated_data:
            instance.set_password(validated_data["password"])

        instance.save()
        return instance
