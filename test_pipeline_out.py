from apps.sentiment.scorer import SentimentScorer
scorer = SentimentScorer()
scorer._load()
res = scorer._pipeline("This is a test of the system.")
print("Single text result:", res)
res_batch = scorer._pipeline(["Test one", "Test two"])
print("Batch result:", res_batch)
