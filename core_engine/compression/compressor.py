"""
Hardwareless AI — Cognitive Compressor Main
"""
import re
import unicodedata
from core_engine.compression.stop_words import STOP_WORDS
from core_engine.compression.synonyms import SYNONYM_MAP

class CognitiveCompressor:
    """
    A LeanCTX-inspired cognitive filter for the Hardwareless AI pipeline.
    """

    def __init__(self, strip_stops=True, normalize_synonyms=True):
        self.strip_stops = strip_stops
        self.normalize_synonyms = normalize_synonyms
        self._stats = {
            "calls": 0,
            "words_in": 0,
            "words_out": 0,
        }

    def compress(self, text):
        """
        Main compression pipeline. Returns cleaned text.
        """
        self._stats["calls"] += 1

        text = unicodedata.normalize("NFKC", text).lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        words = text.split()
        self._stats["words_in"] += len(words)

        if self.strip_stops:
            words = [w for w in words if w not in STOP_WORDS]

        if self.normalize_synonyms:
            words = [SYNONYM_MAP.get(w, w) for w in words]

        deduped = []
        prev = None
        for w in words:
            if w != prev:
                deduped.append(w)
            prev = w
        words = deduped

        self._stats["words_out"] += len(words)

        return " ".join(words)

    @property
    def compression_ratio(self):
        if self._stats["words_in"] == 0:
            return 0.0
        return 1.0 - (self._stats["words_out"] / self._stats["words_in"])

    def get_stats(self):
        return {
            **self._stats,
            "compression_ratio": f"{self.compression_ratio:.1%}",
        }
