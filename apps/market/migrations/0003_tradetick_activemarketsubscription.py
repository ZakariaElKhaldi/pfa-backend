# Generated manually for trade-tick market streaming.

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("tickers", "0003_ticker_sector"),
        ("market", "0002_pricesnapshot_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="TradeTick",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=4, max_digits=12)),
                ("size", models.BigIntegerField(default=0)),
                ("exchange", models.CharField(blank=True, max_length=16)),
                ("trade_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("conditions", models.JSONField(blank=True, default=list)),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("received_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "ticker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trade_ticks",
                        to="tickers.ticker",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="ActiveMarketSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol", models.CharField(db_index=True, max_length=16)),
                ("channel_name", models.CharField(max_length=255, unique=True)),
                ("connected_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(db_index=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="tradetick",
            index=models.Index(fields=["ticker", "-timestamp"], name="market_trad_ticker__e53a4e_idx"),
        ),
        migrations.AddIndex(
            model_name="tradetick",
            index=models.Index(fields=["ticker", "trade_id"], name="market_trad_ticker__ba21c5_idx"),
        ),
        migrations.AddIndex(
            model_name="activemarketsubscription",
            index=models.Index(fields=["symbol", "expires_at"], name="market_acti_symbol_e7228b_idx"),
        ),
    ]
