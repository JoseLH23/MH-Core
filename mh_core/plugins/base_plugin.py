from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """
    Clase base para todos los plugins de MH Core.
    """

    @abstractmethod
    def search(self):
        """
        Debe regresar las oportunidades encontradas.
        """
        pass

    @abstractmethod
    def name(self):
        """
        Nombre del plugin.
        """
        pass