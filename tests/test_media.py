import unittest

from instapull.media import choose_video_frame_count, frame_timestamps


class VideoSamplingTests(unittest.TestCase):
    def test_ten_second_video_uses_five_frames(self):
        self.assertEqual(choose_video_frame_count(10), 5)
        self.assertEqual(
            [round(value, 1) for value in frame_timestamps(10, 5)],
            [1.0, 3.0, 5.0, 7.0, 9.0],
        )

    def test_duration_tiers_are_deterministic(self):
        self.assertEqual(choose_video_frame_count(15), 6)
        self.assertEqual(choose_video_frame_count(30), 10)
        self.assertEqual(choose_video_frame_count(90), 16)
        self.assertEqual(choose_video_frame_count(300), 24)

    def test_long_videos_are_capped_by_configured_max(self):
        self.assertEqual(choose_video_frame_count(600), 24)


if __name__ == "__main__":
    unittest.main()
