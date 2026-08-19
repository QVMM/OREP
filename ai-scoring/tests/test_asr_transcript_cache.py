import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import asr_transcript_cache as cache


class AsrTranscriptCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.upload = Path(self.tmp.name)
        self.settings_patch = patch.object(cache.settings, "UPLOAD_DIR", str(self.upload))
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.sha = "b" * 64

    def test_store_ready_strips_session_and_speaker(self):
        path = cache.store_ready(
            self.sha,
            {
                "transcript": "智能排风系统",
                "duration": 12.5,
                "sessionId": 38,
                "session_id": 38,
                "segments": [
                    {
                        "start": 1.0,
                        "end": 2.0,
                        "text": "智能排风系统",
                        "speaker": "SPEAKER_0",
                        "path": "/uploads/ai-score/38/chunk.wav",
                    }
                ],
            },
        )
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["videoSha256"], self.sha)
        self.assertNotIn("sessionId", payload)
        self.assertNotIn("session_id", payload)
        self.assertEqual(payload["segments"][0]["text"], "智能排风系统")
        self.assertNotIn("speaker", payload["segments"][0])
        self.assertNotIn("path", payload["segments"][0])

    def test_load_ready_rejects_other_recipe_and_invalid_hash(self):
        cache.store_ready(self.sha, {"transcript": "hello", "segments": [{"start": 0, "end": 1, "text": "hello"}]})
        self.assertIsNone(cache.load_ready(self.sha, "asr-cache-v1:other-engine"))
        self.assertIsNone(cache.normalize_video_sha256("../" + "a" * 64))
        self.assertIsNone(cache.load_ready("not-a-hash"))

    def test_get_or_transcribe_reuses_ready_and_force_reruns(self):
        calls = {"n": 0}

        def transcribe():
            calls["n"] += 1
            return {
                "transcript": f"run-{calls['n']}",
                "segments": [{"start": 0, "end": 1, "text": f"run-{calls['n']}"}],
                "duration": 1,
            }

        first = cache.get_or_transcribe(
            project_info={"videoSha256": self.sha},
            video_path=None,
            transcribe=transcribe,
        )
        second = cache.get_or_transcribe(
            project_info={"videoSha256": self.sha},
            video_path=None,
            transcribe=transcribe,
        )
        forced = cache.get_or_transcribe(
            project_info={"videoSha256": self.sha, "forceRetranscribe": True},
            video_path=None,
            transcribe=transcribe,
        )
        self.assertEqual(first["transcript"], "run-1")
        self.assertEqual(second["transcript"], "run-1")
        self.assertTrue(str(second["source"]).startswith("asr_cache:"))
        self.assertEqual(forced["transcript"], "run-2")
        self.assertEqual(calls["n"], 2)

    def test_same_bytes_different_session_share_cache_not_session_payload(self):
        cache.store_ready(
            self.sha,
            {
                "transcript": "同一条带子",
                "segments": [{"start": 0, "end": 1, "text": "同一条带子", "sessionId": 38}],
            },
        )
        reused = cache.to_asr_result(cache.load_ready(self.sha))
        self.assertEqual(reused["transcript"], "同一条带子")
        self.assertEqual(reused["speakers"], [])
        self.assertNotIn("sessionId", reused)


if __name__ == "__main__":
    unittest.main()
