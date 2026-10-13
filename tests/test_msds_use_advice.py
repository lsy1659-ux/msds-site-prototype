"""공급사 칼라 안내가 재생성 뒤에도 남고 원문 안전정보와 섞이지 않는지 확인."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_msds_register import apply_register
from validate_public_release import ValidationResult, validate_msds_register, validate_msds_use_advice


class MsdsUseAdviceTests(unittest.TestCase):
    def valid_advice(self):
        return {"aliases": ["MRM"], "note": "공급사 사용 안내", "source": "공급사 회신",
                "sourceDate": None, "recordedOn": "2026-10-13"}

    def test_unknown_reply_date_is_allowed_without_invention(self):
        advice = self.valid_advice()
        result = ValidationResult()
        validate_msds_use_advice(advice, result, "sample")
        self.assertEqual(result.errors, [])
        self.assertIsNone(advice["sourceDate"])

    def test_missing_source_invalid_aliases_and_dates_are_blocked(self):
        cases = [("source", ""), ("aliases", "MRM"), ("aliases", ["MRM", None]),
                 ("aliases", ["MRM", "mrm"]), ("recordedOn", ""),
                 ("recordedOn", "2026-02-30"), ("sourceDate", "어제")]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                advice = self.valid_advice()
                advice[field] = value
                result = ValidationResult()
                validate_msds_use_advice(advice, result, "sample")
                self.assertTrue(result.errors)

    def test_malformed_advice_is_reported_without_crashing(self):
        for advice in ("MRM", [], 123):
            with self.subTest(advice=advice):
                result = ValidationResult()
                validate_msds_use_advice(advice, result, "sample")
                self.assertEqual(result.errors[0].code, "MSDS_USE_ADVICE_INVALID")

    def test_changed_or_removed_register_advice_requires_public_data_update(self):
        advice = self.valid_advice()
        product = {"id": "sample", "msdsUseAdvice": advice}
        for current in (None, {**advice, "aliases": ["ISM"]}):
            with self.subTest(current=current), TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "data").mkdir()
                entry = {"status": "pending", "msdsUseAdvice": current}
                (root / "data/msds-register.json").write_text(
                    json.dumps({"products": {"sample": entry}}), encoding="utf-8")
                result = ValidationResult()
                validate_msds_register(root, [product], result)
                self.assertIn("MSDS_USE_ADVICE_OUT_OF_SYNC", {issue.code for issue in result.errors})

    def test_rebuild_preserves_advice_without_changing_source_msds_fields(self):
        register = json.loads((ROOT / "data/msds-register.json").read_text(encoding="utf-8"))
        products = json.loads((ROOT / "data/msds.public.json").read_text(encoding="utf-8"))
        source = [deepcopy(p) for p in products if p["id"] in ("msds-060", "msds-061")]
        for product in source:
            product.pop("msdsUseAdvice", None)
        source_before = deepcopy(source)
        without_advice = deepcopy(register)
        for pid in ("msds-060", "msds-061"):
            without_advice["products"][pid].pop("msdsUseAdvice")
        baseline, _, _ = apply_register(source, [], without_advice, [])
        rebuilt, _, _ = apply_register(source, [], register, [])
        self.assertEqual(source, source_before)
        for actual, original in zip(rebuilt, baseline):
            advice = actual.pop("msdsUseAdvice")
            self.assertEqual(actual, original, "원문 제품명·PDF·번호·날짜·안전정보가 바뀌었다")
            self.assertIsNone(advice["sourceDate"], "미제공 회신일을 만들어서는 안 된다")
            self.assertIn("공급사 회신(사용자 전달)", advice["source"])
            expected = "MRM" if actual["id"] == "msds-060" else "ISM"
            self.assertIn(expected, advice["aliases"])

    def test_advice_is_an_independent_copy_and_can_be_removed_in_register(self):
        advice = {"aliases": ["MRM"], "note": "공급사 사용 안내"}
        entry = {"status": "verified", "msdsNo": "AA00586-0000000459", "msdsUseAdvice": advice}
        register = {"products": {"sample": entry}}
        source = [{"id": "sample", "ingredients": [], "signalWord": "위험"}]
        products, _, _ = apply_register(source, [], register, [])
        products[0]["msdsUseAdvice"]["aliases"].append("RM")
        self.assertEqual(advice["aliases"], ["MRM"])
        entry.pop("msdsUseAdvice")
        removed, _, _ = apply_register(products, [], register, [])
        self.assertNotIn("msdsUseAdvice", removed[0])


if __name__ == "__main__":
    unittest.main()
