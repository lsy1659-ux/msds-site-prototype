import unittest

from scripts.extract_pdf_summary import extract_ingredients, extract_revision_date


class ExtractPdfSummaryTests(unittest.TestCase):
    def test_revision_date_prefers_final_revision_over_issue_date(self):
        lines = [
            "나. 최초 작성일 : 1998-03-09",
            "다. 개정 횟수 및 최종 개정 일자 : 6회 2026-06-25",
        ]
        self.assertEqual(extract_revision_date(lines), "2026-06-25")

    def test_revision_date_does_not_fall_back_to_issue_date(self):
        self.assertEqual(extract_revision_date(["최초 작성일 : 2024-04-11"]), "")

    def test_noroo_ingredient_range_is_split_from_chemical_name(self):
        ingredients = extract_ingredients(
            "(1-메틸에틸)벤젠 (1-Methylethyl)benzene 98-82-8 0.1∼0.6"
        )
        self.assertEqual(len(ingredients), 1)
        self.assertEqual(ingredients[0]["casNo"], "98-82-8")
        self.assertEqual(ingredients[0]["content"], "0.1~0.6")
        self.assertNotIn("0.1", ingredients[0]["chemicalName"])


if __name__ == "__main__":
    unittest.main()
