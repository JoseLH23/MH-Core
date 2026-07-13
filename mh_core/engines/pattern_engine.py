from collections import Counter
import re


class PatternEngine:
    """
    Detecta patrones entre los videos encontrados.
    """

    def __init__(self):
        self.name = "Pattern Detection Engine v1"

    def detect_patterns(self, videos):

        if not videos:
            return {
                "common_words": [],
                "top_channels": [],
                "top_queries": [],
                "total_videos": 0
            }

        words = []
        channels = []
        queries = []

        for video in videos:

            title = video.get("title", "")

            clean = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+", title.lower())

            words.extend(clean)

            channels.append(video.get("channel", ""))

            queries.append(video.get("query", ""))

        stop_words = {
            "de","la","el","los","las","un","una",
            "y","en","por","para","con","del",
            "como","qué","que","a","tu","es","al"
        }

        filtered = [
            w for w in words
            if len(w) > 3 and w not in stop_words
        ]

        common_words = Counter(filtered).most_common(10)

        top_channels = Counter(channels).most_common(5)

        top_queries = Counter(queries).most_common(5)

        return {
            "common_words": common_words,
            "top_channels": top_channels,
            "top_queries": top_queries,
            "total_videos": len(videos)
        }