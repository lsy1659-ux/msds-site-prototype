import tempfile
import unittest
from pathlib import Path

from scripts.build_public_data import (
    build_payload,
    build_public_records,
    parse_iso_date,
    validate_pdf_path,
    validate_publication,
)


class BuildPublicDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "pdf").mkdir()
        (self.root / "pdf" / "approved.pdf").write_bytes(b"%PDF-1.4\n")
        (self.root / "pdf" / "product#1.pdf").write_bytes(b"%PDF-1.4\n")
        self.product = {
            "id": "msds-test",
            "productName": "테스트 제품",
            "fileName": "approved.pdf",
            "pdfPath": "pdf/approved.pdf",
            "category": "원재료",
            "supplier": "테스트 공급사",
            "issueDate": "2024-01-01",
            "revisionDate": "2025-01-01",
            "hazardStatements": ["H315 피부에 자극을 일으킴"],
            "ghsCodes": ["GHS07"],
            "privateMemo": "공개되면 안 되는 내부 메모",
        }
        self.override = {
            "match": {"fileName": "approved.pdf", "internalKey": "secret"},
            "sourcePdfPath": "pdf/approved.pdf",
            "sourceRelativePath": "approved.pdf",
            "reviewStatus": "검토완료",
            "reviewedAt": "2026-07-17T09:00:00",
            "reviewedBy": "개인 이름",
            "revisionDateCandidate": "2025-01-01",
            "signalWordCandidate": "경고",
            "hazardStatements": ["H315 피부에 자극을 일으킴"],
            "notes": "내부 자동추출 메모",
            "extractionMeta": {"method": "test"},
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_automatic_summary_is_public_without_manual_review(self):
        self.override["reviewStatus"] = "검토필요"
        products, overrides, stats = build_public_records([self.product], [self.override], self.root)

        self.assertEqual(products[0]["productName"], "테스트 제품")
        self.assertEqual(products[0]["hazardStatements"], self.product["hazardStatements"])
        self.assertNotIn("privateMemo", products[0])
        self.assertTrue(products[0]["publication"]["summaryAvailable"])
        self.assertEqual(products[0]["publication"]["validationStatus"], "automatic")
        self.assertEqual(overrides[0]["signalWordCandidate"], "경고")
        self.assertNotIn("reviewStatus", overrides[0])
        self.assertNotIn("notes", overrides[0])
        self.assertNotIn("extractionMeta", overrides[0])
        self.assertEqual(stats["automaticSummary"], 1)

    def test_public_data_keeps_only_allowlisted_summary_fields(self):
        products, overrides, stats = build_public_records([self.product], [self.override], self.root)

        self.assertTrue(products[0]["publication"]["summaryAvailable"])
        self.assertEqual(products[0]["hazardStatements"], self.product["hazardStatements"])
        self.assertEqual(overrides[0]["signalWordCandidate"], "경고")
        self.assertNotIn("reviewedBy", overrides[0])
        self.assertNotIn("notes", overrides[0])
        self.assertEqual(overrides[0]["match"], {"fileName": "approved.pdf"})
        self.assertEqual(stats["automaticSummary"], 1)

    def test_revision_conflict_removes_only_candidate_date(self):
        self.override["revisionDateCandidate"] = "2024-12-31"
        products, overrides, stats = build_public_records([self.product], [self.override], self.root)

        self.assertTrue(products[0]["publication"]["summaryAvailable"])
        self.assertIn("REVISION_DATE_CONFLICT", products[0]["publication"]["validationWarnings"])
        self.assertEqual(products[0]["hazardStatements"], self.product["hazardStatements"])
        self.assertNotIn("revisionDateCandidate", overrides[0])
        self.assertEqual(stats["automaticSummary"], 1)

    def test_date_order_and_signal_word_are_field_warnings(self):
        self.product["issueDate"] = "2025-02-01"
        self.product["revisionDate"] = "2025-01-01"
        self.override["signalWordCandidate"] = "1/17"
        available, warnings, status = validate_publication(self.product, self.override, self.root)

        self.assertTrue(available)
        self.assertEqual(status, "automatic_with_warnings")
        self.assertIn("ISSUE_DATE_AFTER_REVISION_DATE", warnings)
        self.assertIn("SIGNAL_WORD_INVALID", warnings)
        self.assertIsNone(parse_iso_date("20250101"))

    def test_invalid_signal_word_is_removed_without_hiding_summary(self):
        self.override["signalWordCandidate"] = "(GHS KR)"
        products, overrides, _ = build_public_records([self.product], [self.override], self.root)

        self.assertTrue(products[0]["publication"]["summaryAvailable"])
        self.assertNotIn("signalWordCandidate", overrides[0])
        self.assertEqual(overrides[0]["hazardStatements"], self.override["hazardStatements"])

    def test_pdf_path_must_be_pdf_directory_file(self):
        self.assertIsNone(validate_pdf_path("pdf/approved.pdf", self.root))
        self.assertIsNone(validate_pdf_path("pdf/product#1.pdf", self.root))
        self.assertEqual(validate_pdf_path("pdf/../secret.pdf", self.root), "PDF_PATH_INVALID")
        self.assertEqual(validate_pdf_path("https://example.com/file.pdf", self.root), "PDF_PATH_INVALID")
        self.assertEqual(validate_pdf_path("pdf/missing.pdf", self.root), "PDF_FILE_NOT_FOUND")

    def test_object_payload_does_not_copy_unknown_metadata(self):
        payload = build_payload(
            {"schemaVersion": 2, "privateBuildNote": "secret", "products": []},
            "products",
            [{"id": "safe"}],
        )
        self.assertEqual(payload, {"schemaVersion": 2, "products": [{"id": "safe"}]})


if __name__ == "__main__":
    unittest.main()
