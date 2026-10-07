import tempfile
from pathlib import Path
import unittest
import hashlib

from backend.audio.ffmpeg_utils import compute_audio_hash, compute_legacy_audio_hash

class TestAudioHashing(unittest.TestCase):
    def test_canonical_streaming_sha256(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"Mock audio data" * 100000
            f.write(test_content)
            temp_path = Path(f.name)

        try:
            expected_hash = hashlib.sha256(test_content).hexdigest().lower()
            computed_hash = compute_audio_hash(temp_path)
            self.assertEqual(len(computed_hash), 64)
            self.assertEqual(computed_hash, expected_hash)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_legacy_hash_computation(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_content = b"Small file"
            f.write(test_content)
            temp_path = Path(f.name)

        try:
            legacy_hash = compute_legacy_audio_hash(temp_path)
            self.assertEqual(len(legacy_hash), 16)
        finally:
            temp_path.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
