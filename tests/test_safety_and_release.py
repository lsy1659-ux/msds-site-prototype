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


class FullVerificationTests(unittest.TestCase):
    """2026-10-08 전체 대조. 218건 그림문자는 원문 2항 그림을 눈으로, 문구·응급조치는 원문 글과 줄마다 맞췄다.

    고친 값은 data/msds-content-repairs.json 의 verified·ghsCodes 에 원문 PDF·확인일·까닭과 함께 있다.
    """

    BROKEN = set("싞늒맊홖젂핚짂갂숚렦맋핛젗벖첛얶옦젘앆젃")
    JUNK = re.compile(r"SARAYA|CO\.,?\s*LTD|SAFETY DATA SHEET|PRODUCT\s*NAME|Date (?:revised|prepared)|페이지\s*\d|"
                      r"\(\s*\d+\s*/\s*\d+\s*\)|물질\s*안전\s*보건\s*자료|^\s*[마바]\s*\.\s|신호어\s*[:：]", re.I)

    @classmethod
    def setUpClass(cls):
        cls.products, cls.by_file, cls.register = audit.load()
        cls.by_id = {p["id"]: p for p in cls.products}
        cls.repairs = json.loads((ROOT / "data" / "msds-content-repairs.json").read_text(encoding="utf-8"))

    def shown(self, pid):
        product = self.by_id[pid]
        return audit.shown(product, self.by_file.get(product.get("fileName"), {}))

    def test_verified_text_is_what_the_screen_shows(self):
        for pid, fix in self.repairs["verified"].items():
            view, product = self.shown(pid), self.by_id[pid]
            if "hazardStatements" in fix:
                self.assertEqual(view["hazards"], fix["hazardStatements"]["after"], pid)
            if "precautionaryStatements" in fix:
                for group, lines in fix["precautionaryStatements"]["after"].items():
                    self.assertEqual((view["precautions"] or {}).get(group) or [], lines, f"{pid} {group}")
            for key, change in (fix.get("firstAid") or {}).items():
                self.assertEqual((product.get("firstAid") or {}).get(key) or [], change["after"], f"{pid} {key}")

    def test_no_broken_font_characters(self):
        for name in ("msds.public.json", "msds-overrides.public.json"):
            text = (ROOT / "data" / name).read_text(encoding="utf-8")
            self.assertFalse(set(text) & self.BROKEN, f"{name} 에 글꼴이 깨진 글자가 남았다")

    def test_no_page_headers_or_company_names_in_safety_text(self):
        bad = []
        for product in self.products:
            view = self.shown(product["id"])
            lines = list(view["hazards"]) + [x for g in (view["precautions"] or {}).values() for x in g or []]
            lines += [x for g in (product.get("firstAid") or {}).values() for x in g or []]
            bad += [f"{product['productName']}: {x[:40]}" for x in lines if self.JUNK.search(str(x))]
        self.assertEqual(bad, [])

    def test_gas_first_aid_follows_the_source(self):
        """프로판·부탄 MSDS 에 없는 '구토를 유발하지 마시오'가 응급조치에 들어가 있었다."""
        propane = self.by_id["msds-pdf-53b098ac5f0be241"]["firstAid"]
        self.assertEqual(propane["ingestion"], ["긴급 의료조치를 받으시오"])
        for pid in ("msds-pdf-53b098ac5f0be241", "msds-pdf-5e875f5e2847e4d0"):
            text = json.dumps(self.by_id[pid]["firstAid"], ensure_ascii=False)
            self.assertNotIn("구토를 유발하지", text, pid)

    def test_broken_font_product_restored(self):
        """TH0261(N): 글꼴이 깨진 PDF 라 유해·위험문구·예방조치·응급조치가 통째로 빠져 있었다."""
        view = self.shown("msds-009")
        self.assertEqual(len(view["hazards"]), 13)
        self.assertGreaterEqual(sum(len(x) for x in view["precautions"].values()), 33)
        self.assertEqual(set(self.by_id["msds-009"]["firstAid"]), {"eye", "skin", "inhalation", "ingestion", "note"})
        self.assertEqual(self.by_id["msds-009"]["ghsCodes"], ["GHS02", "GHS07", "GHS08"])

    def test_first_aid_lines_start_where_the_source_does(self):
        self.assertTrue(self.by_id["msds-162"]["firstAid"]["eye"][0].startswith("즉시 오염된 눈은"))
        self.assertTrue(self.by_id["msds-156"]["firstAid"]["eye"][0].startswith("즉시 충분한 양의"))
        self.assertTrue(self.by_id["msds-157"]["firstAid"]["eye"][0].startswith("즉시 많은 양의"))
        self.assertTrue(self.by_id["msds-131"].get("firstAid"), "아세톤 응급조치가 비어 있다")

    def test_pictogram_precedence(self):
        """고시 우선순위: 해골이 있으면 느낌표를 붙이지 않고, 부식성이 있으면 피부·눈 자극 느낌표를 붙이지 않는다."""
        self.assertEqual(audit.required_pictograms({"H331", "H315", "H336"}), {"GHS06"})
        self.assertEqual(audit.required_pictograms({"H290", "H315"}), {"GHS05"})
        self.assertEqual(audit.required_pictograms({"H334", "H317"}), {"GHS08"})
        self.assertEqual(audit.required_pictograms({"H302", "H318"}), {"GHS05", "GHS07"})

    def test_skull_with_exclamation_only_where_supplier_was_asked(self):
        both = [p["id"] for p in self.products if {"GHS06", "GHS07"} <= set(p.get("ghsCodes") or [])]
        for pid in both:
            self.assertTrue(self.register.get(pid, {}).get("sourceIssue"), f"{pid}: 해골·느낌표를 함께 두는 까닭이 관리대장에 없다")

    def test_pictogram_fixes_from_the_full_review(self):
        ghs = {p["id"]: p.get("ghsCodes") for p in self.products}
        self.assertEqual(ghs["msds-013"], ["GHS02", "GHS06", "GHS08"])
        self.assertEqual(ghs["msds-154"], ["GHS05", "GHS07", "GHS09"])
        self.assertEqual(ghs["msds-160"], ["GHS05", "GHS08"])
        self.assertEqual(ghs["msds-167"], ["GHS05", "GHS07", "GHS09"])
        for pid in ("msds-pdf-d53b862679ad3157", "msds-pdf-d353876f24b4839c", "msds-pdf-d462ab4576452226", "msds-pdf-f60438c81a0521d8"):
            self.assertEqual(ghs[pid], ["GHS07"], pid)


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
