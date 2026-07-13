from mh_core.plugins.youtube_plugin import YouTubePlugin


class PluginManager:

    def __init__(self):
        self.plugins = {}

        self.register(YouTubePlugin())

    def register(self, plugin):
        self.plugins[plugin.name().lower()] = plugin

    def get_plugin(self, name):
        return self.plugins.get(name.lower())

    def list_plugins(self):
        return list(self.plugins.keys())

    def run_plugin(self, name):

        plugin = self.get_plugin(name)

        if plugin is None:
            raise ValueError(f"Plugin '{name}' no encontrado.")

        return {
            "plugin": plugin.name(),
            "data": plugin.search()
        }