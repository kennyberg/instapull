import base64
import unittest

from instapull.providers.base import AnalysisContext, MediaFrame
from instapull.providers.ollama import OllamaProvider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return {"response": "Summary: local analysis"}


class FakeSession:
    def __init__(self):
        self.requests = []

    def post(self, url, json, timeout):
        self.requests.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(json)


class OllamaProviderTests(unittest.TestCase):
    def test_image_payload_uses_local_generate_endpoint(self):
        session = FakeSession()
        provider = OllamaProvider(
            model="qwen2.5vl",
            base_url="http://localhost:11434",
            session=session,
        )

        result = provider.describe_image(
            MediaFrame(data=b"image-bytes"),
            AnalysisContext(post_type="image", post_url="https://example.com"),
        )

        self.assertEqual(result, "Summary: local analysis")
        request = session.requests[0]
        self.assertEqual(request["url"], "http://localhost:11434/api/generate")
        self.assertEqual(request["json"]["model"], "qwen2.5vl")
        self.assertEqual(request["json"]["images"], [base64.b64encode(b"image-bytes").decode("ascii")])
        self.assertFalse(request["json"]["stream"])

    def test_video_payload_includes_all_frames(self):
        session = FakeSession()
        provider = OllamaProvider(session=session)

        provider.describe_video(
            [
                MediaFrame(data=b"frame-1", timestamp_seconds=1.0),
                MediaFrame(data=b"frame-2", timestamp_seconds=3.0),
            ],
            AnalysisContext(post_type="video", post_url="https://example.com"),
        )

        payload = session.requests[0]["json"]
        self.assertEqual(len(payload["images"]), 2)
        self.assertIn("Frame 1 at 1.0 seconds", payload["prompt"])
        self.assertIn("Frame 2 at 3.0 seconds", payload["prompt"])


if __name__ == "__main__":
    unittest.main()
