import unittest
from backend.sources.audio_source import YouTubeReferenceSource

class TestYouTubeUrlValidation(unittest.TestCase):
    def test_valid_youtube_urls(self):
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtu.be/dQw4w9WgXcQ",
        ]
        for url in valid_urls:
            extracted = YouTubeReferenceSource._extract_video_id(url)
            self.assertEqual(
                extracted,
                "dQw4w9WgXcQ",
                f"Failed to extract correct video_id from valid URL: {url}"
            )

    def test_invalid_and_malicious_urls(self):
        invalid_urls = [
            "https://youtube.com.attacker.example/watch?v=dQw4w9WgXcQ",
            "https://notyoutube.com/watch?v=dQw4w9WgXcQ",
            "https://user:password@www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com:8080/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=short",
            "https://www.youtube.com/watch?v=toolongvideoid12345",
            "https://www.youtube.com/watch?v=invalid!chars",
            "https://youtu.be/",
            "not a url",
            "",
        ]
        for url in invalid_urls:
            extracted = YouTubeReferenceSource._extract_video_id(url)
            self.assertIsNone(
                extracted,
                f"Expected None for invalid/malicious URL but got {extracted}: {url}"
            )

    def test_authorized_audio_available_flag(self):
        source = YouTubeReferenceSource("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        # Without local audio file, authorized_audio_available must be False
        self.assertFalse(source.is_authorized_audio_available())
        meta = source.get_metadata()
        self.assertFalse(meta.get("authorized_audio_available"))

if __name__ == "__main__":
    unittest.main()
