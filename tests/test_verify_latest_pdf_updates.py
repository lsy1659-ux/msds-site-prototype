import unittest

from scripts.verify_latest_pdf_updates import record_auto_validation


class VerifyLatestPdfUpdatesTests(unittest.TestCase):
    def test_auto_validation_cannot_grant_human_review_approval(self):
        override = {"reviewStatus": "검토필요"}

        record_auto_validation(override, "passed", [], "2026-07-17T09:00:00")

        self.assertEqual(override["reviewStatus"], "검토필요")
        self.assertEqual(override["autoValidation"]["status"], "passed")
        self.assertEqual(override["autoValidation"]["errors"], [])
        self.assertNotIn("reviewedAt", override)
        self.assertNotIn("reviewedBy", override)

    def test_auto_validation_preserves_existing_human_decision(self):
        override = {"reviewStatus": "수정필요", "reviewedBy": "안전보건 담당자"}

        record_auto_validation(override, "failed", ["날짜 불일치"], "2026-07-17T09:00:00")

        self.assertEqual(override["reviewStatus"], "수정필요")
        self.assertEqual(override["reviewedBy"], "안전보건 담당자")
        self.assertEqual(override["autoValidation"]["errors"], ["날짜 불일치"])


if __name__ == "__main__":
    unittest.main()
