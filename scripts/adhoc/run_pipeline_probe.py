import os, django, logging
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

# Stream all logs to stdout so we can see what's happening
logging.basicConfig(level=logging.DEBUG, format="%(name)s [%(levelname)s] %(message)s")

from apps.pipeline.pipeline import run_pipeline_for_ticker

print("\n=== RUNNING PIPELINE FOR AAPL ===\n")
try:
    run_pipeline_for_ticker("AAPL")
    print("\n=== PIPELINE COMPLETED ===")
except Exception as e:
    import traceback
    print(f"\n=== PIPELINE RAISED: {e} ===")
    traceback.print_exc()
