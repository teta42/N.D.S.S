from rest_framework import serializers
from .models import Note, CustomUser
from django.contrib.auth import authenticate

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = '__all__'
        extra_kwargs = {
            'note_id': {'read_only': True},
            'created_at': {'read_only': True},
            'read_count': {'read_only': True},
        }

    def create(self, validated_data):
        # Получаем пользователя из контекста
        user = self.context['request'].user

        # Извлекаем нужные поля из validated_data
        content = validated_data.get('content')
        read_only = validated_data.get('read_only', True)
        dead_line = validated_data.get('dead_line')
        deletion_on_first_reading = validated_data.get('deletion_on_first_reading', False)
        only_authorized = validated_data.get('only_authorized', False)

        # Вызываем кастомный метод create_note
        return Note.objects.create_note(
            user=user,
            content=content,
            read_only=read_only,
            dead_line=dead_line,
            deletion_on_first_reading=deletion_on_first_reading,
            only_authorized=only_authorized
        )

    def update(self, instance, validated_data):
        # Тут можно реализовать логику обновления, если нужно
        # Например:
        instance.content = validated_data.get('content', instance.content)
        instance.read_only = validated_data.get('read_only', instance.read_only)
        instance.dead_line = validated_data.get('dead_line', instance.dead_line)
        instance.deletion_on_first_reading = validated_data.get('deletion_on_first_reading', instance.deletion_on_first_reading)
        instance.only_authorized = validated_data.get('only_authorized', instance.only_authorized)
        instance.save()
        return instance
    
    
class RegSeri(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }
        
    def validate_username(self, value):
        unique = CustomUser.objects.filter(username=value).exists()
        
        if unique:
            raise serializers.ValidationError('This username is already taken')
        
        return value
    
    def create(self, validated_data):
        return CustomUser.objects.create_user(username=validated_data['username'], 
                                              password=validated_data['password'])
        
class LoginSer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }
        
    def validate_username(self, value):
        if not CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('User does not exist.')
        return value
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            raise serializers.ValidationError({'password': 'Incorrect password.'})

        data['user'] = user
        return data