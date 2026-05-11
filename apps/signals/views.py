from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import (
    IsAdmin,
    IsAnalystOrAdmin,
    ScopedAPIKeyPermission,
    ScopedUserPermission,
)
from django.db.models import Q
from apps.tickers.models import Watchlist

from .models import AlertFlag, DecisionLog, SignalAccuracy, SignalSnapshot
from .serializers import (
    AlertFlagSerializer,
    DecisionLogSerializer,
    SignalAccuracySerializer,
    SignalSnapshotSerializer,
)


class SignalPagePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class DecisionLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class OptionalPaginationListAPIView(generics.ListAPIView):
    """
    Backward compatible:
    - no page/page_size => legacy plain array response
    - with page or page_size => DRF paginated envelope
    """

    pagination_class = SignalPagePagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if "page" in request.query_params or "page_size" in request.query_params:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TickerSignalView(APIView):
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["signals.read"]

    def get(self, request, symbol):
        snap = SignalSnapshot.objects.filter(ticker__symbol=symbol).order_by("-created_at").first()
        if snap is None:
            return Response({"detail": "No signal yet."}, status=status.HTTP_404_NOT_FOUND)
        return Response(SignalSnapshotSerializer(snap).data)


class TickerSignalHistoryView(OptionalPaginationListAPIView):
    serializer_class = SignalSnapshotSerializer
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["signals.read"]

    def get_queryset(self):
        return SignalSnapshot.objects.filter(
            ticker__symbol=self.kwargs["symbol"]
        ).order_by("-created_at")


class TickerSignalExplainView(APIView):
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["signals.read"]

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


class TickerSignalAccuracyView(OptionalPaginationListAPIView):
    serializer_class = SignalAccuracySerializer
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["signals.read"]

    def get_queryset(self):
        return SignalAccuracy.objects.filter(
            signal_snapshot__ticker__symbol=self.kwargs["symbol"]
        ).order_by("-evaluated_at")


class AlertListView(generics.ListAPIView):
    serializer_class = AlertFlagSerializer
    permission_classes = [
        IsAuthenticated,
        IsAnalystOrAdmin,
        ScopedAPIKeyPermission,
        ScopedUserPermission,
    ]
    required_scopes = ["alerts.read"]

    def get_queryset(self):
        qs = AlertFlag.objects.select_related("ticker").all()
        resolved = self.request.query_params.get("resolved", "false")
        if resolved == "true":
            qs = qs.filter(resolved=True)
        elif resolved in ("false", ""):
            qs = qs.filter(resolved=False)
        elif resolved != "all":
            qs = qs.filter(resolved=False)

        alert_type = self.request.query_params.get("type")
        if alert_type:
            qs = qs.filter(type=alert_type)

        ticker = self.request.query_params.get("ticker")
        if ticker:
            qs = qs.filter(ticker__symbol__icontains=ticker)

        return qs.order_by("-created_at")


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
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]
    pagination_class = DecisionLogPagination

    def get_queryset(self):
        qs = DecisionLog.objects.select_related("ticker").all()
        symbol = self.request.query_params.get("ticker")
        if symbol:
            qs = qs.filter(ticker__symbol=symbol.upper())
        signal = self.request.query_params.get("signal")
        if signal in ("BUY", "SELL", "HOLD"):
            qs = qs.filter(engine_output__signal=signal)
        method = self.request.query_params.get("method")
        if method:
            qs = qs.filter(Q(engine_output__method=method) | Q(scoring_detail__method=method))
        date_from = self.request.query_params.get("from")
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        date_to = self.request.query_params.get("to")
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        return qs


class DecisionLogDetailView(generics.RetrieveAPIView):
    serializer_class = DecisionLogSerializer
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]
    queryset = DecisionLog.objects.all()


class RecentSignalsView(OptionalPaginationListAPIView):
    serializer_class = SignalSnapshotSerializer
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["signals.read"]

    def get_queryset(self):
        try:
            limit = max(1, min(int(self.request.query_params.get("limit", 20)), 100))
        except (ValueError, TypeError):
            limit = 20
        if (
            self.request.query_params.get("all") == "true"
            and getattr(self.request.user, "role", None) == "admin"
        ):
            return SignalSnapshot.objects.order_by("-created_at")[:limit]
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
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["signals.read"]

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
