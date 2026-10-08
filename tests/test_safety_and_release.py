"""안전문구 검증·배포 안전장치 (2026-10-08 GPT 2차 점검 반영).

  - 안전문구끼리 어긋나는 것(구토·신호어)은 관리대장에 공급사 확인으로 적혀 있어야 한다.
  - 원문 확인을 적은 뒤 그 PDF 가 바뀌면 다시 보게 한다.
  - 화면 파일을 고치면 판 번호(지문)를 올려야 한다.
  - 제품 수 기준은 data/release-policy.json 한 곳.
  - 날짜 읽기·문구 꼴 고치기의 새 규칙.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_safety_consistency as audit  # noqa: E402
import bump_asset_version as bump  # noqa: E402
import msds_pdf_text as pdf_text  # noqa: E402
import normalize_public_content as normalize  # noqa: E402


class SafetyConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products, cls.by_file, cls.register = audit.load()
        cls.findings = audit.check_rules(cls.products, cls.by_file, cls.register) \
            + audit.check_evidence(cls.products, cls.register)

    def test_contradictions_are_recorded_as_supplier_questions(self):
        """구토·신호어 어긋남은 원문을 보고 관리대장에 sourceIssue 로 적혀 있어야 한다."""
        open_high = [f for f in self.findings if f["level"] == "높음" and not f["acknowledged"]]
        self.assertEqual(open_high, [], "관리대장에 안 적힌 어긋남: "
                         + "; ".join(f"{f['productName']} {f['message'][:40]}" for f in open_high))

    def test_tc317_vomiting_conflict_is_flagged_not_rewritten(self):
        product = next(p for p in self.products if p["id"] == "msds-033")
        self.assertIn("구토를 시키시오", " ".join(product["firstAid"]["ingestion"]), "원문 문장은 그대로 둔다")
        entry = self.register["msds-033"]
        self.assertIn("P331", entry.get("sourceIssue", ""))
        self.assertTrue(entry.get("sourceIssueAsk"))
        evidence = entry.get("sourceIssueEvidence") or {}
        for field in ("checkedOn", "sha256", "page", "pdf"):
            self.assertTrue(evidence.get(field), f"검토 근거에 {field} 가 없다")

    def test_screen_and_audit_use_the_same_vomiting_rule(self):
        js = (ROOT / "js" / "safety-notes.js").read_text(encoding="utf-8")
        for name in ("INDUCE_VOMIT", "NEGATED"):
            js_pattern = re.search(rf"const {name} = /(.*?)/;", js).group(1)
            self.assertEqual(js_pattern, getattr(audit, name).pattern, f"{name} 가 화면과 점검 스크립트에서 다르다")
        for name in ("app.js", "guide.js"):
            self.assertIn("window.MsdsSafety?.vomitConflict(", (ROOT / "js" / name).read_text(encoding="utf-8"), name)

    def test_negated_sentence_is_not_a_conflict(self):
        self.assertIsNone(audit.NEGATED.search("구토를 시키시오."))
        self.assertTrue(audit.INDUCE_VOMIT.search("구토를 시키시오."))
        self.assertTrue(audit.NEGATED.search("의식이 없는 경우 구토를 시키지 말고"))

    def test_pictograms_follow_hazard_codes(self):
        """원문 그림을 눈으로 확인해 고친 3건(썬 라이타 가스·캉가루 구두약·피비원)이 들어 있다."""
        repairs = json.loads((ROOT / "data" / "msds-content-repairs.json").read_text(encoding="utf-8"))["ghsCodes"]
        self.assertEqual(repairs["msds-pdf-52d86cde38911013"]["after"], ["GHS05"])
        self.assertIn("GHS07", repairs["msds-pdf-a26053814f066ef9"]["after"])
        self.assertIn("GHS07", repairs["msds-pdf-838acfd9993bcf72"]["after"])
        # 그림문자가 비어 경고표지가 '그림문자가 붙지 않는 분류'로 나가던 2차이형제(S6)
        self.assertEqual(repairs["msds-077"]["after"], ["GHS02", "GHS08"])
        product = next(p for p in self.products if p["id"] == "msds-077")
        self.assertEqual(product.get("ghsCodes"), ["GHS02", "GHS08"])
        missing = [f for f in self.findings if f["rule"] == "그림문자" and not f["acknowledged"]]
        self.assertEqual(missing, [], "H코드가 요구하는 그림문자가 빠진 제품: " + ", ".join(f["productName"] for f in missing))


class DateReaderTests(unittest.TestCase):
    def test_revision_history_that_continues_on_the_next_page(self):
        text = ("다. 개정횟수 및 최종 개정일자 :\n 16차/2019.01.16, 20차/2022.04.06,\n\n"
                "PRODUCT NAME PAGE\nK1 (케이 1) ( 14 / 14 )\n\n21차//2022.07.13\n라. 기타")
        self.assertEqual(pdf_text.revision_date(text), "2022-07-13")

    def test_english_labels(self):
        text = "Date Created First : 2011-08-10\nDate of last revision : 2025-08-13\n"
        self.assertEqual(pdf_text.revision_date(text), "2025-08-13")
        self.assertEqual(pdf_text.issue_date(text), "2011-08-10")

    def test_day_month_year_with_dots(self):
        self.assertEqual(pdf_text.revision_date("개정: 13.04.2017\n"), "2017-04-13")


class StatementShapeTests(unittest.TestCase):
    def test_dumped_section_is_split_and_p_lines_move(self):
        record = {"hazardStatements": [
            "H226 인화성 액체 및 증기.",
            "PP-303 GW(PU)2. 유해성·위험성유해·위험 문구:H226 - 인화성 액체 및 증기.H315 - 피부에 자극을 일으킴."
            "H319 - 눈에 심한 자극을 일으킴.예방조치 문구예방:P201 - 사용 전 취급 설명서를 확보하시오."
            "P501 - 폐기물 관련 법령에 따라 내용물/용기를 폐기하시오.유해성·위험성 분류기준에포함되지 않는 기타 유해성",
        ], "precautionaryStatements": {}}
        normalize.normalize_statements(record)
        self.assertEqual(record["hazardStatements"],
                         ["H226 인화성 액체 및 증기.", "H315 피부에 자극을 일으킴.", "H319 눈에 심한 자극을 일으킴."])
        self.assertEqual(record["precautionaryStatements"]["prevention"], ["P201 사용 전 취급 설명서를 확보하시오."])
        self.assertEqual(record["precautionaryStatements"]["disposal"], ["P501 폐기물 관련 법령에 따라 내용물/용기를 폐기하시오."])

    def test_classification_prefix_is_dropped_when_the_sentence_repeats(self):
        record = {"hazardStatements": [
            "H225 Flammable liquids : Category 2 ; Highly flammable liquid and vapour.",
            "H225 Highly flammable liquid and vapour.",
        ]}
        normalize.normalize_statements(record)
        self.assertEqual(record["hazardStatements"], ["H225 Highly flammable liquid and vapour."])

    def test_trailing_section_heading_is_removed(self):
        record = {"precautionaryStatements": {"response": ["P363 다시 사용전 오염된 의복은 세척하시오. 2.2.4.3. 저장"],
                                              "storage": ["P403+P233 용기를 단단히 밀폐하여 저장."]}}
        normalize.normalize_statements(record)
        self.assertEqual(record["precautionaryStatements"]["response"], ["P363 다시 사용전 오염된 의복은 세척하시오."])
        self.assertEqual(record["precautionaryStatements"]["storage"], ["P403+P233 용기를 단단히 밀폐하여 저장."])


class ReleaseGuardTests(unittest.TestCase):
    def test_screen_files_carry_a_fresh_asset_version(self):
        """js·css·html 을 고치고 판 번호를 안 올리면 현장 폰에 옛 화면이 남는다."""
        self.assertEqual(bump.recorded_fingerprint(), bump.shell_fingerprint(),
                         "화면 파일이 바뀌었는데 판 번호를 안 올렸다: py scripts/bump_asset_version.py")

    def test_expected_product_count_lives_in_one_place(self):
        policy = json.loads((ROOT / "data" / "release-policy.json").read_text(encoding="utf-8"))
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        self.assertEqual(policy["expectedProducts"], len(products))
        workflow = (ROOT / ".github" / "workflows" / "validate-msds-release.yml").read_text(encoding="utf-8")
        self.assertNotIn("--expected-products", workflow, "제품 수를 워크플로에 따로 적지 않는다")
        self.assertIn("bump_asset_version.py --check", workflow)
        self.assertNotIn("\n    paths:\n", workflow, "CI 가 고른 경로만 보면 html·sw.js 변경이 검증 없이 올라간다")

    def test_review_edits_keep_evidence(self):
        source = (ROOT / "js" / "review.js").read_text(encoding="utf-8")
        for word in ("reviewLog", "pdfSha256", "page", "reviewer", "before", "after"):
            self.assertIn(word, source)


if __name__ == "__main__":
    unittest.main()
