"""
VectorMemoryStore — búsqueda semántica real sobre las memorias
guardadas, con TF-IDF + similitud coseno, en Python puro (sin numpy ni
scikit-learn — con el volumen real de memorias de este proyecto,
decenas o cientos de registros, no miles de millones, no hace falta
una dependencia nueva para esto).

No es un "vector DB" externo (Pinecone/Weaviate/etc, todos de pago o
que requieren infraestructura aparte) — es un índice vectorial real,
local y gratis, que resuelve el problema real pedido: encontrar
memorias relacionadas por SIGNIFICADO, no por coincidencia exacta de
texto. Si el volumen de memorias crece a punto de necesitar algo más
(miles de registros, baja latencia), este archivo es el único que
habría que reemplazar por un cliente de un vector DB real — el
contrato (buscar_similares) no cambiaría.
"""
import math
import re
from collections import Counter

PALABRAS_VACIAS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "a",
    "que", "es", "con", "para", "por", "su", "se", "al", "lo", "como",
}


def _tokenizar(texto: str) -> list[str]:
    palabras = re.findall(r"[a-záéíóúñü0-9]+", (texto or "").lower())
    return [p for p in palabras if p not in PALABRAS_VACIAS and len(p) > 1]


class VectorMemoryStore:
    def __init__(self, documentos: dict[str, str]):
        """`documentos`: {id_memoria: texto_a_indexar}. Se construye el
        índice TF-IDF completo al momento — barato con el volumen real
        de memorias de este proyecto."""
        self._ids = list(documentos.keys())
        self._tokens_por_doc = {doc_id: _tokenizar(texto) for doc_id, texto in documentos.items()}
        self._idf = self._calcular_idf()
        self._vectores = {doc_id: self._vectorizar(tokens) for doc_id, tokens in self._tokens_por_doc.items()}

    def _calcular_idf(self) -> dict[str, float]:
        n_docs = max(len(self._tokens_por_doc), 1)
        doc_frecuencia = Counter()
        for tokens in self._tokens_por_doc.values():
            for palabra in set(tokens):
                doc_frecuencia[palabra] += 1
        return {palabra: math.log((n_docs + 1) / (df + 1)) + 1 for palabra, df in doc_frecuencia.items()}

    def _vectorizar(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        conteo = Counter(tokens)
        total = len(tokens)
        return {palabra: (freq / total) * self._idf.get(palabra, 0.0) for palabra, freq in conteo.items()}

    @staticmethod
    def _similitud_coseno(a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        claves_comunes = set(a) & set(b)
        producto_punto = sum(a[k] * b[k] for k in claves_comunes)
        norma_a = math.sqrt(sum(v * v for v in a.values()))
        norma_b = math.sqrt(sum(v * v for v in b.values()))
        if norma_a == 0 or norma_b == 0:
            return 0.0
        return producto_punto / (norma_a * norma_b)

    def buscar_similares(self, consulta: str, k: int = 5) -> list[tuple[str, float]]:
        """Devuelve [(id_memoria, score)] ordenado por similitud
        semántica real, más relevante primero. Score 0 = sin relación."""
        vector_consulta = self._vectorizar(_tokenizar(consulta))
        puntuaciones = [
            (doc_id, self._similitud_coseno(vector_consulta, vector))
            for doc_id, vector in self._vectores.items()
        ]
        puntuaciones.sort(key=lambda par: par[1], reverse=True)
        return [par for par in puntuaciones if par[1] > 0][:k]
