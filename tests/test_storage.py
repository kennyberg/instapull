import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from instapull.storage import SavedPost, update_json_index


class StorageTests(unittest.TestCase):
    def test_video_analysis_metadata_is_written_to_index(self):
        post = SavedPost(
            post_id="abc123",
            username="demo",
            post_url="https://example.com/p/abc123",
            image_url="https://example.com/image.jpg",
            video_url="https://example.com/video.mp4",
            caption="hello #tag",
            hashtags=["tag"],
            date="2026-05-31",
            post_type="video",
            location=None,
            ai_description="Summary: demo",
            ai_provider="gemini",
            ai_model="gemini-2.5-flash-lite",
            ai_media_type="video",
            ai_frames_analyzed=5,
        )

        with TemporaryDirectory() as tmp:
            index_path = update_json_index([post], Path(tmp))
            index_text = index_path.read_text(encoding="utf-8")

        self.assertIn('"ai_provider": "gemini"', index_text)
        self.assertIn('"ai_frames_analyzed": 5', index_text)
        self.assertIn('"video_url": "https://example.com/video.mp4"', index_text)


if __name__ == "__main__":
    unittest.main()
