from rest_framework import serializers

from damcup.models import DamCup, SeasonLongPoints, Scores
from register.serializers import SimplePlayerSerializer


class DamCupSerializer(serializers.ModelSerializer):

    class Meta:
        model = DamCup
        fields = ("id", "season", "good_guys", "bad_guys", "site", )


class SeasonLongPointsSerializer(serializers.ModelSerializer):

    player = SimplePlayerSerializer()

    class Meta:
        model = SeasonLongPoints
        fields = ("id", "additional_info", "event", "player", "gross_points", "net_points", )


class ScoresSerializer(serializers.ModelSerializer):

    player = SimplePlayerSerializer()

    class Meta:
        model = Scores
        fields = ("id", "event", "player", "hole", "score", )
