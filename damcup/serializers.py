from rest_framework import serializers

from damcup.models import DamCup


class DamCupSerializer(serializers.ModelSerializer):

    class Meta:
        model = DamCup
        fields = ("id", "season", "good_guys", "bad_guys", "site", )
