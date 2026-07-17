import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_public_release import (
    ValidationResult,
    build_release_manifest,
    check_release_manifest,
    validate_public_release,
    write_json,
)


class PublicReleaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "data").mkdir()
        (self.root / "js").mkdir()
        (self.root / "pdf").mkdir()
        (self.root / "js" / "app.js").write_text(
            "const APP_CONFIG = { allowCandidateOverrideDisplay: false };\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def product(self, product_id="p-1", pdf_path="pdf/a.pdf"):
        return {
            "id": product_id,
            "productName": "시험 제품",
            "fileName": Path(pdf_path).name,
            "pdfPath": pdf_path,
            "issueDate": "2024-01-01",
            "revisionDate": "2024-02-01",
            "signalWord": "위험",
            "hazardStatements": ["H226"],
            "publication": {
                "reviewStatus": "검토완료",
                "approvedForDisplay": True,
                "validationStatus": "passed",
                "validationErrors": [],
            },
        }

    def override(self, pdf_path="pdf/a.pdf"):
        return {
            "sourcePdfPath": pdf_path,
            "match": {"fileName": Path(pdf_path).name},
            "reviewStatus": "검토완료",
            "revisionDateCandidate": "2024-02-01",
            "signalWordCandidate": "위험",
            "publication": {
                "reviewStatus": "검토완료",
                "approvedForDisplay": True,
                "validationStatus": "passed",
                "validationErrors": [],
            },
        }

    def write_release(self, products=None, overrides=None, pdfs=("pdf/a.pdf",)):
        for relative in pdfs:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"%PDF-1.4\n%%EOF\n")
        write_json(self.root / "data/msds.public.json", products or [self.product()])
        write_json(self.root / "data/msds-overrides.public.json", overrides or [self.override()])

    def codes(self, result):
        return {issue.code for issue in result.issues}

    def test_valid_reviewed_release_passes(self):
        self.write_release()

        result = validate_public_release(self.root, expected_products=1)

        self.assertEqual(result.errors, [])
        self.assertEqual(result.stats["linkedProducts"], 1)
        self.assertEqual(result.stats["approvedProducts"], 1)

    def test_duplicate_id_and_pdf_are_blocked(self):
        products = [self.product(), self.product()]
        self.write_release(products=products)

        result = validate_public_release(self.root, expected_products=2)

        self.assertIn("DUPLICATE_PRODUCT_ID", self.codes(result))
        self.assertIn("DUPLICATE_PRODUCT_PDF", self.codes(result))

    def test_unreviewed_candidate_and_summary_cannot_be_public(self):
        product = {
            "id": "p-1",
            "productName": "시험 제품",
            "fileName": "a.pdf",
            "pdfPath": "pdf/a.pdf",
            "revisionDate": "2024-02-01",
            "hazardStatements": ["H226"],
            "publication": {
                "reviewStatus": "검토필요",
                "approvedForDisplay": False,
                "validationStatus": "not_reviewed",
                "validationErrors": [],
            },
        }
        override = {
            "sourcePdfPath": "pdf/a.pdf",
            "match": {"fileName": "a.pdf"},
            "reviewStatus": "검토필요",
            "revisionDateCandidate": "2024-02-01",
            "publication": {
                "reviewStatus": "검토필요",
                "approvedForDisplay": False,
                "validationStatus": "not_reviewed",
                "validationErrors": [],
            },
        }
        self.write_release(products=[product], overrides=[override])

        result = validate_public_release(self.root, expected_products=1)

        self.assertIn("UNAPPROVED_PRODUCT_SUMMARY_EXPOSED", self.codes(result))
        self.assertIn("UNREVIEWED_OVERRIDE_CANDIDATE_EXPOSED", self.codes(result))

    def test_identity_only_unreviewed_record_is_safe(self):
        product = {
            "id": "p-1",
            "productName": "시험 제품",
            "fileName": "a.pdf",
            "pdfPath": "pdf/a.pdf",
            "publication": {
                "reviewStatus": "검토필요",
                "approvedForDisplay": False,
                "validationStatus": "not_reviewed",
                "validationErrors": [],
            },
        }
        override = {
            "sourcePdfPath": "pdf/a.pdf",
            "match": {"fileName": "a.pdf"},
            "reviewStatus": "검토필요",
            "publication": {
                "reviewStatus": "검토필요",
                "approvedForDisplay": False,
                "validationStatus": "not_reviewed",
                "validationErrors": [],
            },
        }
        self.write_release(products=[product], overrides=[override])

        result = validate_public_release(self.root, expected_products=1)

        self.assertEqual(result.errors, [])
        self.assertEqual(result.stats["reviewRequiredProducts"], 1)

    def test_reviewed_date_conflict_and_invalid_signal_word_are_blocked(self):
        override = self.override()
        override["revisionDateCandidate"] = "2024-03-01"
        override["signalWordCandidate"] = "(GHS KR)"
        self.write_release(overrides=[override])

        result = validate_public_release(self.root, expected_products=1)

        self.assertIn("REVISION_DATE_CONFLICT", self.codes(result))
        self.assertIn("SIGNAL_WORD_INVALID", self.codes(result))

    def test_missing_pdf_is_blocked(self):
        self.write_release(pdfs=())

        result = validate_public_release(self.root, expected_products=1)

        self.assertIn("PDF_FILE_NOT_FOUND", self.codes(result))

    def test_manifest_detects_changed_pdf(self):
        self.write_release()
        result = validate_public_release(self.root, expected_products=1)
        manifest = build_release_manifest(
            self.root,
            result,
            data_cutoff_date="2026-06-30",
            generated_at="2026-07-17T00:00:00Z",
            commit_sha="abc123",
        )
        manifest_path = Path("data/release-manifest.json")
        write_json(self.root / manifest_path, manifest)

        clean_check = ValidationResult()
        clean_check.stats.update(result.stats)
        check_release_manifest(self.root, manifest_path, manifest, clean_check)
        self.assertEqual(clean_check.errors, [])

        (self.root / "pdf/a.pdf").write_bytes(b"changed")
        changed_manifest = build_release_manifest(
            self.root,
            result,
            data_cutoff_date="2026-06-30",
            generated_at="2026-07-17T00:00:00Z",
            commit_sha="abc123",
        )
        stale_check = ValidationResult()
        stale_check.stats.update(result.stats)
        check_release_manifest(self.root, manifest_path, changed_manifest, stale_check)
        self.assertIn("RELEASE_MANIFEST_STALE", self.codes(stale_check))


if __name__ == "__main__":
    unittest.main()
