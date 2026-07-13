from mh_core.plugins.base_plugin import BasePlugin
from mh_core.research import run_research


class YouTubePlugin(BasePlugin):

    def name(self):
        return "YouTube"

    def search(self):
        return run_research()