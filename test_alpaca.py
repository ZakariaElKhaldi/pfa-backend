from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

client = NewsClient("fake_key", "fake_secret") # We don't have keys, but we can inspect the response or type
print("Alpaca Client Created")

# To test the class NewsSet
from alpaca.data.models.news import NewsSet
print("NewsSet dir:", dir(NewsSet))
