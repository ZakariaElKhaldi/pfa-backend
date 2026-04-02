from decimal import Decimal
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.tickers.models import Ticker
from apps.market.models import PriceSnapshot
from .models import Portfolio, Position, Trade
from .serializers import PortfolioSerializer


def get_or_create_portfolio():
    portfolio, _ = Portfolio.objects.get_or_create(id=1, defaults={"name": "My Portfolio"})
    return portfolio


def get_latest_price(ticker: Ticker) -> Decimal:
    snap = PriceSnapshot.objects.filter(ticker=ticker).order_by("-timestamp").first()
    if snap is None:
        raise ValueError(f"No price available for {ticker.symbol}")
    return snap.price


class PortfolioView(APIView):
    def get(self, request):
        portfolio = get_or_create_portfolio()
        return Response(PortfolioSerializer(portfolio).data)


class BuyView(APIView):
    def post(self, request):
        symbol = request.data.get("symbol", "").upper()
        quantity = int(request.data.get("quantity", 0))
        if quantity <= 0:
            return Response({"detail": "quantity must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            return Response({"detail": f"{symbol} not tracked"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price = get_latest_price(ticker)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        total_cost = price * quantity
        portfolio = get_or_create_portfolio()

        if portfolio.cash < total_cost:
            return Response(
                {"detail": f"Insufficient funds: need {total_cost}, have {portfolio.cash}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        position, _ = Position.objects.get_or_create(
            portfolio=portfolio, ticker=ticker, defaults={"quantity": 0, "avg_price": price}
        )
        # Recalculate avg price
        total_shares = position.quantity + quantity
        position.avg_price = (
            (position.avg_price * position.quantity + price * quantity) / total_shares
        )
        position.quantity = total_shares
        position.save()

        portfolio.cash -= total_cost
        portfolio.save(update_fields=["cash"])

        Trade.objects.create(portfolio=portfolio, ticker=ticker, side=Trade.SIDE_BUY, quantity=quantity, price=price)

        return Response(PortfolioSerializer(portfolio).data)


class SellView(APIView):
    def post(self, request):
        symbol = request.data.get("symbol", "").upper()
        quantity = int(request.data.get("quantity", 0))
        if quantity <= 0:
            return Response({"detail": "quantity must be positive"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            return Response({"detail": f"{symbol} not tracked"}, status=status.HTTP_400_BAD_REQUEST)

        portfolio = get_or_create_portfolio()

        try:
            position = Position.objects.get(portfolio=portfolio, ticker=ticker)
        except Position.DoesNotExist:
            return Response({"detail": "No position in this ticker"}, status=status.HTTP_400_BAD_REQUEST)

        if position.quantity < quantity:
            return Response(
                {"detail": f"Only {position.quantity} shares owned"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            price = get_latest_price(ticker)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        position.quantity -= quantity
        if position.quantity == 0:
            position.delete()
        else:
            position.save(update_fields=["quantity"])

        portfolio.cash += price * quantity
        portfolio.save(update_fields=["cash"])

        Trade.objects.create(portfolio=portfolio, ticker=ticker, side=Trade.SIDE_SELL, quantity=quantity, price=price)

        return Response(PortfolioSerializer(portfolio).data)
