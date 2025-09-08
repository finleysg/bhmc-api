from rest_framework import serializers
from register.serializers import SimplePlayerSerializer
from events.serializers import SimpleEventSerializer
from courses.serializers import CourseSerializer, HoleSerializer
from .models import SkinTransaction, Skin, SkinSettings

class SkinTransactionSerializer(serializers.ModelSerializer):
    player = SimplePlayerSerializer(read_only=True)

    class Meta:
        model = SkinTransaction
        fields = ("id", "player", "season", "transaction_type", "transaction_amount", 
                 "transaction_date", "transaction_timestamp", "direction")

class SkinSerializer(serializers.ModelSerializer):
    player = SimplePlayerSerializer(read_only=True)
    event = SimpleEventSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    hole = HoleSerializer(read_only=True)

    class Meta:
        model = Skin
        fields = ("id", "event", "course", "hole", "player", "skin_type", 
                 "skin_amount", "is_team")

class SkinSettingsSerializer(serializers.ModelSerializer):
    player = SimplePlayerSerializer(read_only=True)

    class Meta:
        model = SkinSettings
        fields = ("id", "player", "payment_frequency")

class SimpleSkinSerializer(serializers.ModelSerializer):
    """Simplified serializer for nested use"""
    
    class Meta:
        model = Skin
        fields = ("id", "skin_type", "skin_amount", "is_team")

class SimpleSkinTransactionSerializer(serializers.ModelSerializer):
    """Simplified serializer for nested use"""
    
    class Meta:
        model = SkinTransaction
        fields = ("id", "transaction_type", "transaction_amount", "transaction_date", "direction")
