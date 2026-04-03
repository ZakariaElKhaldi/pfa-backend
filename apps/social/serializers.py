from rest_framework import serializers

from .models import SocialPost


class SocialPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialPost
        fields = [
            "id",
            "source",
            "external_id",
            "title",
            "url",
            "content",
            "sentiment_score",
            "sentiment_label",
            "posted_at",
            "fetched_at",
        ]
