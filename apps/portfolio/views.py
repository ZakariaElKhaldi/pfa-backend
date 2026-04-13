from decimal import Decimal

from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker

from .models import Portfolio, Position, Trade
from .serializers import PortfolioSerializer, TradeSerializer


def get_portfolio(user):
    portfolio, _ = Portfolio.objects.get_or_create(
        user=user, defaults={"cash": Decimal("100000.00")}
    )
    return portfolio


def get_latest_price(ticker: Ticker) -> Decimal:
    snap = PriceSnapshot.objects.filter(ticker=ticker).order_by("-timestamp").first()
    if snap is None:
        raise ValueError(f"No price available for {ticker.symbol}")
    return snap.price


class PortfolioView(APIView):
    def get(self, request):
        portfolio = get_portfolio(request.user)
        return Response(PortfolioSerializer(portfolio).data)


class BuyView(APIView):
    def post(self, request):
        symbol = request.data.get("symbol", "").upper()
        try:
            quantity = int(request.data.get("quantity", 0))
        except (ValueError, TypeError):
            return Response(
                {"detail": "quantity must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quantity <= 0:
            return Response(
                {"detail": "quantity must be positive"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            return Response({"detail": f"{symbol} not tracked"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price = get_latest_price(ticker)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        total_cost = price * quantity

        with transaction.atomic():
            portfolio = Portfolio.objects.select_for_update().get_or_create(
                user=request.user, defaults={"cash": Decimal("100000.00")}
            )[0]

            if portfolio.cash < total_cost:
                return Response(
                    {"detail": f"Insufficient funds: need {total_cost}, have {portfolio.cash}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            position, _ = Position.objects.select_for_update().get_or_create(
                portfolio=portfolio, ticker=ticker, defaults={"quantity": 0, "avg_price": price}
            )
            total_shares = position.quantity + quantity
            position.avg_price = (
                position.avg_price * position.quantity + price * quantity
            ) / total_shares
            position.quantity = total_shares
            position.save()

            portfolio.cash -= total_cost
            portfolio.save(update_fields=["cash"])

            Trade.objects.create(
                portfolio=portfolio,
                ticker=ticker,
                side=Trade.SIDE_BUY,
                quantity=quantity,
                price=price,
            )

        return Response(PortfolioSerializer(portfolio).data)


class SellView(APIView):
    def post(self, request):
        symbol = request.data.get("symbol", "").upper()
        try:
            quantity = int(request.data.get("quantity", 0))
        except (ValueError, TypeError):
            return Response(
                {"detail": "quantity must be a valid integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quantity <= 0:
            return Response(
                {"detail": "quantity must be positive"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            return Response({"detail": f"{symbol} not tracked"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price = get_latest_price(ticker)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            portfolio = Portfolio.objects.select_for_update().get_or_create(
                user=request.user, defaults={"cash": Decimal("100000.00")}
            )[0]

            try:
                position = Position.objects.select_for_update().get(
                    portfolio=portfolio, ticker=ticker
                )
            except Position.DoesNotExist:
                return Response(
                    {"detail": "No position in this ticker"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if position.quantity < quantity:
                return Response(
                    {"detail": f"Only {position.quantity} shares owned"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            position.quantity -= quantity
            if position.quantity == 0:
                position.delete()
            else:
                position.save(update_fields=["quantity"])

            portfolio.cash += price * quantity
            portfolio.save(update_fields=["cash"])

            Trade.objects.create(
                portfolio=portfolio,
                ticker=ticker,
                side=Trade.SIDE_SELL,
                quantity=quantity,
                price=price,
            )

        return Response(PortfolioSerializer(portfolio).data)


class PortfolioSummaryView(APIView):
    def get(self, request):
        portfolio = get_portfolio(request.user)
        total_positions_value = Decimal("0")
        cost_basis = Decimal("0")
        for position in portfolio.positions.select_related("ticker").all():
            try:
                price = get_latest_price(position.ticker)
            except (ValueError, Exception):
                price = position.avg_price
            total_positions_value += price * position.quantity
            cost_basis += position.avg_price * position.quantity
        total_value = portfolio.cash + total_positions_value
        total_pnl = total_positions_value - cost_basis
        total_pnl_pct = (
            float(total_pnl / cost_basis * 100) if cost_basis else 0.0
        )
        return Response({
            "cash": str(portfolio.cash),
            "total_positions_value": str(total_positions_value),
            "total_value": str(total_value),
            "total_pnl": str(total_pnl),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "position_count": portfolio.positions.count(),
        })


class TradeListView(generics.ListAPIView):
    serializer_class = TradeSerializer
    pagination_class = None

    def get_queryset(self):
        portfolio = get_portfolio(self.request.user)
        return Trade.objects.filter(portfolio=portfolio).order_by("-executed_at")
