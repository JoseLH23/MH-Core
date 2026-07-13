import json
from pathlib import Path


class KnowledgeEngine:

    def __init__(self):
        self.base_path = Path("mh_core/database/knowledge")

    def _load(self, filename):
        path = self.base_path / filename

        if not path.exists():
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    def _save(self, filename, data):
        path = self.base_path / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def update_topic(self, topic):

        data = self._load("topics.json")

        data[topic] = data.get(topic, 0) + 1

        self._save("topics.json", data)

    def update_channel(self, channel):

        data = self._load("channels.json")

        data[channel] = data.get(channel, 0) + 1

        self._save("channels.json", data)

    def get_topics(self):
        return self._load("topics.json")

    def get_channels(self):
        return self._load("channels.json")