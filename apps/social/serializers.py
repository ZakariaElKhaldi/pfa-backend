from rest_framework import serializers

from .models import SocialPost


class SocialPostSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    display_content = serializers.SerializerMethodField()
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    def get_content(self, obj: SocialPost) -> str:
        return obj.cleaned_text or obj.content

    def get_display_content(self, obj: SocialPost) -> str:
        return obj.cleaned_text or obj.content

    class Meta:
        model = SocialPost
        fields = [
            "id",
            "ticker",
            "ticker_symbol",
            "source",
            "external_id",
            "title",
            "url",
            "content",
            "cleaned_text",
            "display_content",
            "sentiment_score",
            "sentiment_label",
            "posted_at",
            "fetched_at",
        ]
