import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
from apps.accounts.models import CustomUser
from apps.analytics.services import run_backtest

user = CustomUser.objects.first()
end = timezone.now()
start = end - timedelta(days=30)

try:
    run = run_backtest(
        user=user,
        symbol="AAPL",
        start=start,
        end=end,
        strategy="sentiment_threshold",
        params={"threshold": 0.6}
    )
    print(f"Success! Trades: {len(run.trades)}, Return: {run.total_return}")
except Exception as e:
    import traceback
    traceback.print_exc()
