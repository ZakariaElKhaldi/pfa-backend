from apps.tickers.models import Ticker
from apps.pipeline.pipeline import run_pipeline_for_ticker
from django.db import DataError

ticker, _ = Ticker.objects.get_or_create(symbol='MSFT', defaults={'name': 'Microsoft'})
try:
    run_pipeline_for_ticker(ticker.symbol)
except DataError as e:
    import traceback
    traceback.print_exc()
