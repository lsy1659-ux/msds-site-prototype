"""공급사 칼라 안내가 재생성 뒤에도 남고 원문 안전정보와 섞이지 않는지 확인."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_msds_register import apply_register


class MsdsUseAdviceTests(unittest.TestCase):
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
