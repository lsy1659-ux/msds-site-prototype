import unittest

from scripts.reconcile_selected_pdf_records import content_without_id, id_score, identity_key
from scripts.apply_reference_product_updates import PRESERVED_FIELDS


class ReconcileSelectedPdfRecordsTests(unittest.TestCase):
    def test_duplicate_identity_ignores_record_id(self):
        first = {"id": "msds-013", "fileName": "PUB795101 (KR).pdf", "productName": "R-255 경화제(캠스)", "msdsNo": "AA00875-9152795101"}
        second = {**first, "id": "msds-034"}
        self.assertEqual(identity_key(first), identity_key(second))
        self.assertEqual(content_without_id(first), content_without_id(second))

    def test_older_stable_id_is_kept(self):
        first = {"id": "msds-013"}
        second = {"id": "msds-034"}
        self.assertLess(id_score(first), id_score(second))

    def test_reference_update_cannot_overwrite_pdf_dates(self):
        self.assertTrue({"issueDate", "preparationDate", "revisionDate"}.issubset(PRESERVED_FIELDS))


if __name__ == "__main__":
    unittest.main()
