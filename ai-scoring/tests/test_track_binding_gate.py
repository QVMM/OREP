import unittest

from fastapi import BackgroundTasks

from app.routers.session_scoring_router import SessionScoringRequest, score_session
from app.services.scoring.track_binding import (
    TrackConfirmationRequired,
    validate_competition_binding,
)


def official_binding():
    return {
        "competitionName": "2026年校级创新创业竞赛",
        "trackId": "33",
        "trackName": "商贸赛道",
        "groupName": "高职组",
        "ruleVersion": "v1.2-engine-draft",
        "ruleHash": "sha256:test-rule",
        "selectionSource": "user_selected",
        "confirmedAt": "2026-07-13T14:00:00+08:00",
        "confirmedBy": "user:1",
    }


class TrackBindingGateTest(unittest.IsolatedAsyncioTestCase):
    def test_missing_track_is_rejected_for_official_publication(self):
        with self.assertRaisesRegex(TrackConfirmationRequired, "track_confirmation_required"):
            validate_competition_binding({}, publish_official_score=True)

    def test_plain_legacy_track_name_is_not_confirmation(self):
        with self.assertRaisesRegex(TrackConfirmationRequired, "track_confirmation_required"):
            validate_competition_binding(
                {"trackName": "商贸赛道"},
                publish_official_score=True,
            )

    def test_complete_user_selected_binding_can_publish_officially(self):
        normalized = validate_competition_binding(
            official_binding(),
            publish_official_score=True,
        )

        self.assertEqual(normalized["bindingStatus"], "confirmed")
        self.assertEqual(normalized["publicationMode"], "official")
        self.assertEqual(normalized["selectionSource"], "user_selected")

    def test_diagnostic_override_requires_non_official_publication(self):
        binding = {
            "trackName": "商贸赛道",
            "ruleVersion": "v1.2-engine-draft",
            "ruleHash": "sha256:test-rule",
            "selectionSource": "diagnostic_override",
        }
        with self.assertRaisesRegex(TrackConfirmationRequired, "track_confirmation_required"):
            validate_competition_binding(binding, publish_official_score=True)

        normalized = validate_competition_binding(binding, publish_official_score=False)
        self.assertEqual(normalized["bindingStatus"], "diagnostic_assumption")
        self.assertEqual(normalized["publicationMode"], "diagnostic")

    async def test_router_rejects_unconfirmed_request_before_queueing_task(self):
        background_tasks = BackgroundTasks()
        request = SessionScoringRequest(
            sessionId=999,
            sessionNo="SC-TEST",
            trackName="商贸赛道",
            videoFilePath="/tmp/test.mp4",
            callbackUrl="http://127.0.0.1/callback",
        )

        response = await score_session(request, background_tasks)

        self.assertFalse(response.accepted)
        self.assertEqual(response.message, "track_confirmation_required")
        self.assertEqual(background_tasks.tasks, [])

    async def test_router_accepts_java_uploaded_video_diagnostic_binding(self):
        background_tasks = BackgroundTasks()
        binding = {
            "trackId": "track-it",
            "trackName": "新一代信息技术赛道",
            "ruleVersion": "v1.2",
            "ruleHash": "sha256:test",
            "selectionSource": "diagnostic_override",
        }
        request = SessionScoringRequest(
            sessionId=25,
            sessionNo="SC-20260713161131314",
            teamId=2,
            projectId=2,
            trackId="track-it",
            trackName="新一代信息技术赛道",
            competitionBinding=binding,
            publishOfficialScore=False,
            juryEnabled=True,
            videoFilePath="/tmp/test.mp4",
            callbackUrl="http://127.0.0.1/callback",
        )

        response = await score_session(request, background_tasks)

        self.assertTrue(response.accepted)
        self.assertEqual(response.taskId, "session-25")
        self.assertEqual(len(background_tasks.tasks), 1)
        task = background_tasks.tasks[0]
        self.assertFalse(task.kwargs["publish_official_score"])
        self.assertTrue(task.kwargs["jury_enabled"])
        self.assertEqual(task.kwargs["competition_binding"]["selectionSource"], "diagnostic_override")
        self.assertEqual(task.kwargs["competition_binding"]["publicationMode"], "diagnostic")


if __name__ == "__main__":
    unittest.main()
