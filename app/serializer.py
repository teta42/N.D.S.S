from rest_framework import serializers
from django.contrib.auth import authenticate

from .models import Note, CustomUser


# Сериализатор заметок
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = "__all__"
        extra_kwargs = {
            "note_id": {"read_only": True},
            "created_at": {"read_only": True},
            "read_count": {"read_only": True},
        }

    def create(self, validated_data):
        user = self.context["request"].user

        content = validated_data.get("content")
        read_only = validated_data.get("read_only", True)
        dead_line = validated_data.get("dead_line")
        deletion_on_first_reading = validated_data.get("deletion_on_first_reading", False)
        only_authorized = validated_data.get("only_authorized", False)

        return Note.objects.create_note(
            user=user,
            content=content,
            read_only=read_only,
            dead_line=dead_line,
            deletion_on_first_reading=deletion_on_first_reading,
            only_authorized=only_authorized,
        )

    def update(self, instance, validated_data):
        instance.content = validated_data.get("content", instance.content)
        instance.read_only = validated_data.get("read_only", instance.read_only)
        instance.dead_line = validated_data.get("dead_line", instance.dead_line)
        instance.deletion_on_first_reading = validated_data.get(
            "deletion_on_first_reading", instance.deletion_on_first_reading
        )
        instance.only_authorized = validated_data.get("only_authorized", instance.only_authorized)
        instance.save()
        return instance


# Регистрация пользователя
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["username", "password"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Это имя пользователя уже занято.")
        return value

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

    class Meta:
        model = CustomUser
        fields = ["username", "password"]

    def validate_username(self, value):
        current_user = self.instance
        if current_user and current_user.username == value:
            return value

        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Это имя пользователя уже занято.")

        return value

    def update(self, instance, validated_data):
        instance.username = validated_data.get("username", instance.username)

        password = validated_data.get("password")
        if password:
            instance.set_password(password)

        instance.save()
        return instance

