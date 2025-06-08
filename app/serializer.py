from rest_framework import serializers

class NoteSerializer(serializers.Serializer):
    content = serializers.CharField()
    read_only = serializers.BooleanField()
    dead_line = serializers.DateTimeField()
    deletion_on_first_reading = serializers.BooleanField()
    only_authorized = serializers.BooleanField()