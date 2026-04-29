import csv
import io
from datetime import timedelta

from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market.models import PriceSnapshot
from apps.portfolio.models import Portfolio, Trade
from apps.signals.models import AlertFlag, SignalSnapshot
from apps.social.models import SocialPost
from apps.tickers.models import Ticker, Watchlist


def _coerce_row(row):
    """Convert datetime values in a dict to ISO format strings."""
    return {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()}


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """Bypass DRF's ?format= interception so the view can read
    ?format=csv as a plain query param. Scoped to TickerExportView."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)


@method_decorator(ratelimit(key="user", rate="5/m", method="GET", block=True), name="get")
class TickerExportView(APIView):
    content_negotiation_class = IgnoreClientContentNegotiation
    renderer_classes = [JSONRenderer]

    MAX_EXPORT_ROWS = 10_000

    def get(self, request, symbol):
        try:
            ticker = Ticker.objects.get(symbol=symbol.upper())
        except Ticker.DoesNotExist:
            return Response({"detail": "Ticker not found"}, status=status.HTTP_404_NOT_FOUND)

        fmt = request.query_params.get("format", "json")
        include_raw = request.query_params.get("include", "posts,signals,prices,alerts")
        includes = [s.strip() for s in include_raw.split(",")]

        def _parse_date(raw, default):
            if not raw:
                return default
            dt = parse_datetime(raw)
            if dt is None:
                raise ValueError(f"Invalid datetime format: {raw!r}. Use ISO 8601.")
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            return dt

        try:
            date_from = _parse_date(
                request.query_params.get("from"),
                timezone.now() - timedelta(days=30),
            )
            date_to = _parse_date(
                request.query_params.get("to"),
                timezone.now(),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        data = {}

        if "posts" in includes:
            post_fields = (
                "source",
                "content",
                "cleaned_text",
                "sentiment_score",
                "sentiment_label",
                "posted_at",
            )
            data["posts"] = list(
                SocialPost.objects.filter(
                    ticker=ticker, fetched_at__gte=date_from, fetched_at__lte=date_to
                ).values(*post_fields)[: self.MAX_EXPORT_ROWS]
            )

        if "signals" in includes:
            data["signals"] = list(
                SignalSnapshot.objects.filter(
                    ticker=ticker, created_at__gte=date_from, created_at__lte=date_to
                ).values(
                    "signal", "sentiment", "momentum", "consistency", "post_count", "created_at"
                )[: self.MAX_EXPORT_ROWS]
            )

        if "prices" in includes:
            data["prices"] = list(
                PriceSnapshot.objects.filter(
                    ticker=ticker, timestamp__gte=date_from, timestamp__lte=date_to
                ).values("price", "volume", "timestamp")[: self.MAX_EXPORT_ROWS]
            )

        if "alerts" in includes:
            data["alerts"] = list(
                AlertFlag.objects.filter(
                    ticker=ticker, created_at__gte=date_from, created_at__lte=date_to
                ).values(
                    "type", "sentiment", "momentum", "consistency", "resolved", "created_at"
                )[: self.MAX_EXPORT_ROWS]
            )

        if fmt == "csv":
            return self._csv_response(data, symbol)

        # JSON: coerce datetimes to ISO strings
        for key in data:
            data[key] = [_coerce_row(row) for row in data[key]]

        return Response(data)

    def _csv_response(self, data, symbol):
        def generate():
            for section, rows in data.items():
                if not rows:
                    continue
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                yield f"# {section}\n"
                writer.writeheader()
                yield output.getvalue()
                for row in rows:
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                    writer.writerow(_coerce_row(row))
                    yield output.getvalue()
                yield "\n"

        response = StreamingHttpResponse(generate(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{symbol}_export.csv"'
        return response


@method_decorator(ratelimit(key="user", rate="5/m", method="GET", block=True), name="get")
class GlobalSignalExportView(APIView):
    permission_classes = [IsAuthenticated]
    content_negotiation_class = IgnoreClientContentNegotiation
    renderer_classes = [JSONRenderer]

    def get(self, request):
        fmt = request.query_params.get("format", "json")

        watchlist_tickers = Watchlist.objects.filter(
            user=request.user
        ).values_list("ticker_id", flat=True)

        qs = SignalSnapshot.objects.filter(
            ticker_id__in=watchlist_tickers
        ).select_related("ticker").order_by("-created_at")

        from_dt = request.query_params.get("from")
        to_dt = request.query_params.get("to")
        if from_dt:
            try:
                qs = qs.filter(created_at__gte=from_dt)
            except Exception:
                pass
        if to_dt:
            try:
                qs = qs.filter(created_at__lte=to_dt)
            except Exception:
                pass

        if fmt == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="signals.csv"'
            writer = csv.writer(response)
            writer.writerow([
                "symbol", "signal", "sentiment", "momentum", "consistency",
                "prediction_method", "prediction_confidence", "created_at",
            ])
            for s in qs:
                writer.writerow([
                    s.ticker.symbol, s.signal, s.sentiment, s.momentum,
                    s.consistency, s.prediction_method, s.prediction_confidence,
                    s.created_at.isoformat(),
                ])
            return response

        data = [
            {
                "symbol": s.ticker.symbol,
                "signal": s.signal,
                "sentiment": s.sentiment,
                "momentum": s.momentum,
                "consistency": s.consistency,
                "prediction_method": s.prediction_method,
                "prediction_confidence": s.prediction_confidence,
                "created_at": s.created_at.isoformat(),
            }
            for s in qs
        ]
        return Response(data)


class BulkExportView(APIView):
    """GET /api/export/bulk/?symbols=AAPL,MSFT&include=signals,prices&format=csv|json"""

    permission_classes = [IsAuthenticated]
    content_negotiation_class = IgnoreClientContentNegotiation
    renderer_classes = [JSONRenderer]

    MAX_EXPORT_ROWS = 50_000

    def get_permissions(self):
        from apps.accounts.permissions import IsAnalystOrAdmin
        return [IsAuthenticated(), IsAnalystOrAdmin()]

    def get(self, request):
        symbols_raw = request.query_params.get("symbols", "")
        symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
        include_raw = request.query_params.get("include", "signals")
        includes = [s.strip() for s in include_raw.split(",")]
        fmt = request.query_params.get("format", "json")

        ticker_qs = Ticker.objects.all()
        if symbols:
            ticker_qs = ticker_qs.filter(symbol__in=symbols)
        ticker_ids = list(ticker_qs.values_list("id", flat=True))
        if not ticker_ids:
            return Response({"signals": [], "prices": [], "posts": [], "alerts": []})

        data: dict = {}
        if "signals" in includes:
            data["signals"] = [
                {
                    "symbol": s.ticker.symbol,
                    "signal": s.signal,
                    "sentiment": s.sentiment,
                    "momentum": s.momentum,
                    "consistency": s.consistency,
                    "post_count": s.post_count,
                    "created_at": s.created_at.isoformat(),
                }
                for s in (
                    SignalSnapshot.objects
                    .filter(ticker_id__in=ticker_ids)
                    .select_related("ticker")
                    .order_by("-created_at")[: self.MAX_EXPORT_ROWS]
                )
            ]
        if "prices" in includes:
            data["prices"] = [
                {
                    "symbol": p.ticker.symbol,
                    "price": str(p.price),
                    "volume": p.volume,
                    "timestamp": p.timestamp.isoformat(),
                }
                for p in (
                    PriceSnapshot.objects
                    .filter(ticker_id__in=ticker_ids)
                    .select_related("ticker")
                    .order_by("-timestamp")[: self.MAX_EXPORT_ROWS]
                )
            ]
        if "posts" in includes:
            data["posts"] = [
                {
                    "symbol": p.ticker.symbol,
                    "source": p.source,
                    "sentiment_score": p.sentiment_score,
                    "sentiment_label": p.sentiment_label,
                    "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                }
                for p in (
                    SocialPost.objects
                    .filter(ticker_id__in=ticker_ids)
                    .select_related("ticker")
                    .order_by("-posted_at")[: self.MAX_EXPORT_ROWS]
                )
            ]
        if "alerts" in includes:
            data["alerts"] = [
                {
                    "symbol": a.ticker.symbol,
                    "type": a.type,
                    "resolved": a.resolved,
                    "created_at": a.created_at.isoformat(),
                }
                for a in (
                    AlertFlag.objects
                    .filter(ticker_id__in=ticker_ids)
                    .select_related("ticker")
                    .order_by("-created_at")[: self.MAX_EXPORT_ROWS]
                )
            ]

        if fmt == "csv":
            return self._csv_response(data)
        return Response(data)

    def _csv_response(self, data):
        def generate():
            for section, rows in data.items():
                if not rows:
                    continue
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                yield f"# {section}\n"
                writer.writeheader()
                yield output.getvalue()
                for row in rows:
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                    writer.writerow(row)
                    yield output.getvalue()
                yield "\n"

        response = StreamingHttpResponse(generate(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="bulk_export.csv"'
        return response


@method_decorator(ratelimit(key="user", rate="5/m", method="GET", block=True), name="get")
class PortfolioExportView(APIView):
    permission_classes = [IsAuthenticated]
    content_negotiation_class = IgnoreClientContentNegotiation
    renderer_classes = [JSONRenderer]

    def get(self, request):
        fmt = request.query_params.get("format", "json")

        try:
            portfolio = Portfolio.objects.get(user=request.user)
        except Portfolio.DoesNotExist:
            if fmt == "csv":
                response = HttpResponse(content_type="text/csv")
                response["Content-Disposition"] = 'attachment; filename="portfolio.csv"'
                csv.writer(response).writerow(["symbol", "side", "quantity", "price", "executed_at"])
                return response
            return Response([])

        qs = Trade.objects.filter(portfolio=portfolio).select_related("ticker").order_by("-executed_at")

        from_dt = request.query_params.get("from")
        to_dt = request.query_params.get("to")
        if from_dt:
            try:
                qs = qs.filter(executed_at__gte=from_dt)
            except Exception:
                pass
        if to_dt:
            try:
                qs = qs.filter(executed_at__lte=to_dt)
            except Exception:
                pass

        if fmt == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="portfolio.csv"'
            writer = csv.writer(response)
            writer.writerow(["symbol", "side", "quantity", "price", "executed_at"])
            for t in qs:
                writer.writerow([
                    t.ticker.symbol, t.side, t.quantity, str(t.price), t.executed_at.isoformat(),
                ])
            return response

        data = [
            {
                "symbol": t.ticker.symbol,
                "side": t.side,
                "quantity": t.quantity,
                "price": str(t.price),
                "executed_at": t.executed_at.isoformat(),
            }
            for t in qs
        ]
        return Response(data)
