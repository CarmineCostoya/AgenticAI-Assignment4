from pathlib import Path
import tempfile
import unittest

from personal_wiki.config import AppPaths
from personal_wiki.harness import AskService, ChatService
from personal_wiki.models import Passage
from personal_wiki.retrieval import PassageIndex

from tests.helpers import FakeClient


ROOT = Path(__file__).resolve().parents[1]


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.index = PassageIndex(
            Path(self.tempdir.name) / "index.sqlite3",
            {"payment": ["reimbursement"], "access": ["reach"], "approval": ["approved"]},
        )
        self.index.rebuild(
            [
                Passage(
                    "p1",
                    "source-a",
                    "vault/raw/a.pdf",
                    "slide 6",
                    "Regulatory approval alone does not guarantee reimbursement or patient access.",
                )
            ]
        )
        self.paths = AppPaths(ROOT)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_ask_renders_only_validated_citations(self):
        client = FakeClient(
            [
                {
                    "relevant_evidence_ids": ["S1"],
                    "reason": "The passage directly answers the question.",
                },
                {
                    "claims": [{"text": "Approval alone does not ensure access.", "evidence_ids": ["S1"]}],
                }
            ]
        )
        result = AskService(self.paths, self.index, client).ask(
            "Why can an approved product fail to reach a patient?"
        )
        self.assertTrue(result.supported)
        self.assertIn("slide 6", result.rendered_answer)
        self.assertIn("S1", result.rendered_answer)

    def test_unknown_citation_fails_closed(self):
        client = FakeClient(
            [
                {
                    "relevant_evidence_ids": ["S1"],
                    "reason": "The passage directly answers the question.",
                },
                {
                    "claims": [{"text": "Unsupported.", "evidence_ids": ["S99"]}],
                }
            ]
        )
        result = AskService(self.paths, self.index, client).ask(
            "Why can an approved product fail to reach a patient?"
        )
        self.assertFalse(result.supported)
        self.assertIn("failed citation validation", result.rendered_answer)

    def test_insufficient_retrieval_does_not_call_model(self):
        client = FakeClient([])
        result = AskService(self.paths, self.index, client).ask("What is the Chilean percentage in 2026?")
        self.assertFalse(result.supported)
        self.assertEqual([], client.calls)

    def test_capability_chat_never_retrieves(self):
        client = FakeClient([])
        service = ChatService(self.paths, self.index, client)
        result = service.chat("what can you help me with?", [])
        self.assertFalse(result.route.retrieve)
        self.assertIn("brainstorm", result.text)

    def test_generic_plan_followup_uses_history_without_model(self):
        client = FakeClient([])
        service = ChatService(self.paths, self.index, client)
        plan = service.chat("Create a three-step study plan for tomorrow.", [])
        history = [
            {"role": "user", "content": "Create a three-step study plan for tomorrow."},
            {"role": "assistant", "content": plan.text},
        ]
        shorter = service.chat("make that shorter", history)
        self.assertFalse(plan.route.retrieve)
        self.assertFalse(shorter.route.retrieve)
        self.assertIn("practice actively", shorter.text)
        self.assertEqual([], client.calls)

    def test_history_is_limited_to_eight_messages_and_six_thousand_characters(self):
        history = [{"role": "user", "content": "x" * 1000} for _ in range(12)]
        trimmed = ChatService.trim_history(history)
        self.assertLessEqual(len(trimmed), 8)
        self.assertLessEqual(sum(len(item["content"]) for item in trimmed), 6000)


if __name__ == "__main__":
    unittest.main()
