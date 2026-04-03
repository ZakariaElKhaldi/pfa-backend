from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AlertFlag, SignalSnapshot
from .serializers import AlertFlagSerializer, SignalSnapshotSerializer


class TickerSignalView(APIView):
    def get(self, request, symbol):
        snap = SignalSnapshot.objects.filter(ticker__symbol=symbol).order_by("-created_at").first()
        if snap is None:
            return Response({"detail": "No signal yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SignalSnapshotSerializer(snap).data)


class TickerSignalHistoryView(generics.ListAPIView):
    serializer_class = SignalSnapshotSerializer

    def get_queryset(self):
        return SignalSnapshot.objects.filter(
            ticker__symbol=self.kwargs["symbol"]
        ).order_by("-created_at")[:100]


class TickerSignalExplainView(APIView):
    def get(self, request, symbol):
        snap = SignalSnapshot.objects.filter(ticker__symbol=symbol).order_by("-created_at").first()
        if snap is None:
            return Response({"detail": "No signal yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "signal": snap.signal,
            "prediction_method": snap.prediction_method,
            "prediction_confidence": snap.prediction_confidence,
            "feature_importances": snap.feature_importances,
            "aggregation": {
                "bullish_ratio": snap.bullish_ratio,
                "normalized_index": snap.normalized_index,
                "time_decay_score": snap.time_decay_score,
                "source_weighted_score": snap.source_weighted_score,
            },
            "counts": {
                "positive": snap.positive_count,
                "negative": snap.negative_count,
                "neutral": snap.neutral_count,
                "total": snap.post_count,
            },
        })


class AlertListView(generics.ListAPIView):
    serializer_class = AlertFlagSerializer

    def get_queryset(self):
        return AlertFlag.objects.filter(resolved=False).order_by("-created_at")


class AlertResolveView(APIView):
    def patch(self, request, pk):
        try:
            alert = AlertFlag.objects.get(pk=pk)
        except AlertFlag.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alert.resolved = True
        alert.save(update_fields=["resolved"])
        return Response(AlertFlagSerializer(alert).data)
