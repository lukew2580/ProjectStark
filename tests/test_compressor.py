from core_engine.compression.compressor import CognitiveCompressor

def test_basic_compression():
    compressor = CognitiveCompressor()
    text = "The quick brown fox is jumping over the lazy dog"
    compressed = compressor.compress(text)
    # Stops like 'the', 'is' should be gone, and 'quick' becomes 'fast'
    assert "the" not in compressed.split()
    assert "is" not in compressed.split()
    assert "fast" in compressed.split()

def test_synonym_normalization():
    compressor = CognitiveCompressor()
    # 'make' and 'build' should both become 'create'
    assert compressor.compress("make") == "create"
    assert compressor.compress("build") == "create"

def test_deduplication():
    compressor = CognitiveCompressor()
    text = "fast fast slow slow fast"
    # Consecutive repeats should be removed
    assert compressor.compress(text) == "fast slow fast"

def test_stats():
    compressor = CognitiveCompressor()
    compressor.compress("The system is fast")
    stats = compressor.get_stats()
    assert stats["calls"] == 1
    assert stats["words_in"] == 4
    assert stats["words_out"] == 2
