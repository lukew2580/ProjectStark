"""
Hardwareless AI — Hypervector to Text Decoder
"""
from core_engine.brain.operations import similarity

class Decoder:
    def __init__(self, encoder):
        self.encoder = encoder
        self.dimensions = encoder.dimensions

    def decode(self, hypervector, vocabulary):
        """
        Finds the top-N most similar words from a vocabulary to the given vector.
        """
        results = []
        for word in vocabulary:
            word_vec = self.encoder.get_word_vector(word)
            score = similarity(hypervector, word_vec, self.dimensions)
            results.append((word, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def decode_top(self, hypervector, vocabulary, n=3):
        """Returns just the top N matching words as strings."""
        ranked = self.decode(hypervector, vocabulary)
        return [word for word, score in ranked[:n]]

    def synthesize_code(self, hypervector, code_lexicon):
        """
        Reconstructs a structural code snippet from a bundled hypervector.
        Combines structural atoms into a functional string.
        """
        atoms = []
        # code_lexicon is expected to be the global code_atoms dict
        for category, vocab in code_lexicon.items():
            # Find the strongest matching atom in each category
            top_atom = self.decode_top(hypervector, vocab, n=1)
            if top_atom:
                atoms.append(top_atom[0])

        # Basic stitching logic — can be made much more complex for 'Deep' synthesis
        # For now, it assembles a valid one-line structural proposal
        if not atoms:
            return "# No agentic code proposal synthesized."
            
        return " ".join(atoms)
