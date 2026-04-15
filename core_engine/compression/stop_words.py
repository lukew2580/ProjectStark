"""
Hardwareless AI — Stop Words List
These carry almost zero semantic weight. Stripping them reduces the
number of word vectors we need to generate and bundle.
"""
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it",
    "they", "them", "their", "its", "his", "her",
    "this", "that", "these", "those", "which", "who", "whom",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "up", "about", "into", "through", "during", "before", "after",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "just", "also", "than", "very", "too", "quite", "rather",
    "if", "then", "else", "when", "where", "how", "what", "why",
    "all", "each", "every", "any", "some", "no", "few", "more",
    "here", "there", "now", "already", "still", "again",
})
