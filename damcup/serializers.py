from rest_framework import serializers

from damcup.models import DamCup, SeasonLongPoints


class DamCupSerializer(serializers.ModelSerializer):

    class Meta:
        model = DamCup
        fields = ("id", "season", "good_guys", "bad_guys", "site", )


class SeasonLongPointsSerializer(serializers.ModelSerializer):

    class Meta:
        model = SeasonLongPoints
        fields = ("id", "event", "player", "gross_points", "net_points", )
