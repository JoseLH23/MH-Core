import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

YOUTUBE_SEARCH_QUERIES = [
    "inteligencia artificial",
    "neurociencia",
    "tecnología futurista",
    "misterios del universo",
    "datos curiosos ciencia"
]

YOUTUBE_MAX_RESULTS_PER_QUERY = 5
YOUTUBE_REGION_CODE = "MX"
YOUTUBE_RELEVANCE_LANGUAGE = "es"