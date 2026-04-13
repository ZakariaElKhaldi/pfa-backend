from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.tickers.models import Watchlist

from .models import AlertFlag, DecisionLog, SignalAccuracy, SignalSnapshot
from .serializers import (
    AlertFlagSerializer,
    DecisionLogSerializer,
    SignalAccuracySerializer,
    SignalSnapshotSerializer,
)


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


class TickerSignalAccuracyView(generics.ListAPIView):
    serializer_class = SignalAccuracySerializer

    def get_queryset(self):
        return SignalAccuracy.objects.filter(
            signal_snapshot__ticker__symbol=self.kwargs["symbol"]
        ).order_by("-evaluated_at")[:100]


class AlertListView(generics.ListAPIView):
    serializer_class = AlertFlagSerializer

    def get_queryset(self):
        return AlertFlag.objects.filter(resolved=False).order_by("-created_at")


class AlertResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        try:
            alert = AlertFlag.objects.get(pk=pk)
        except AlertFlag.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        alert.resolved = True
        alert.save(update_fields=["resolved"])
        return Response(AlertFlagSerializer(alert).data)


class DecisionLogListView(generics.ListAPIView):
    serializer_class = DecisionLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = DecisionLog.objects.all()
        symbol = self.request.query_params.get("ticker")
        if symbol:
            qs = qs.filter(ticker__symbol=symbol.upper())
        return qs


class DecisionLogDetailView(generics.RetrieveAPIView):
    serializer_class = DecisionLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = DecisionLog.objects.all()


class RecentSignalsView(generics.ListAPIView):
    serializer_class = SignalSnapshotSerializer
    pagination_class = None

    def get_queryset(self):
        limit = min(int(self.request.query_params.get("limit", 20)), 100)
        watchlist_tickers = Watchlist.objects.filter(
            user=self.request.user
        ).values_list("ticker_id", flat=True)
        if not watchlist_tickers:
            return SignalSnapshot.objects.none()
        return (
            SignalSnapshot.objects
            .filter(ticker_id__in=watchlist_tickers)
            .order_by("-created_at")[:limit]
        )


class GlobalAccuracyView(APIView):
    def get(self, request):
        records = SignalAccuracy.objects.filter(accuracy_24h__isnull=False)
        total = records.count()
        if total == 0:
            return Response({"overall_pct": None, "by_signal": {}, "total_evaluated": 0})
        correct = records.filter(accuracy_24h=True).count()
        overall_pct = round(correct / total * 100, 1)
        by_signal = {}
        for sig in ["BUY", "SELL", "HOLD"]:
            sig_records = records.filter(predicted=sig)
            sig_total = sig_records.count()
            if sig_total:
                by_signal[sig] = round(
                    sig_records.filter(accuracy_24h=True).count() / sig_total * 100, 1
                )
        return Response({
            "overall_pct": overall_pct,
            "by_signal": by_signal,
            "total_evaluated": total,
        })
