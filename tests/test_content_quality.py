"""공개 데이터의 문구 꼴, 원본 PDF 대조 보완, 날짜, 재인쇄 표시를 지킨다."""

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import msds_pdf_text as T  # noqa: E402
import normalize_public_content as N  # noqa: E402
import sync_pdf_library  # noqa: E402

CODE = re.compile(r"[HP]\d{3}")
LABEL_HEAD = re.compile(r"^\s*(?:[-•·▪]|예방|대응|저장|폐기|유해\s*[·ㆍᆞ·•,]?\s*위험\s*문구)")


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


class PublicContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = load("msds.public.json")
        cls.overrides = load("msds-overrides.public.json")
        cls.register = load("msds-register.json")
        cls.repairs = load("msds-content-repairs.json")
        cls.by_id = {p["id"]: p for p in cls.products}

    def test_precautions_sit_in_the_group_their_code_names(self):
        """P3 은 대응, P4 는 저장, P5 는 폐기. 예방 칸에 대응 문구가 섞이면 관리요령 사고 시 칸이 빈다."""
        want = {"prevention": "12", "response": "3", "storage": "4", "disposal": "5"}
        for record in self.products + self.overrides:
            for group, items in (record.get("precautionaryStatements") or {}).items():
                for line in items:
                    code = CODE.match(line)
                    if code and code.group(0).startswith("P"):
                        self.assertIn(line[1], want[group], f"{record.get('productName') or record.get('productNameCandidate')}: {group} 칸의 {line[:30]}")

    def test_statements_start_with_their_code_not_a_label(self):
        for product in self.products:
            lines = list(product.get("hazardStatements") or [])
            lines += [x for items in (product.get("precautionaryStatements") or {}).values() for x in items]
            for line in lines:
                self.assertIsNone(LABEL_HEAD.match(line), f"{product['productName']}: 앞머리가 남음 {line[:30]}")

    def test_statement_text_carries_no_classification(self):
        """"H315 피부에 자극을 일으킴 인화성 액체 : 구분2 …" 처럼 분류 칸 글이 문구에 붙으면 표지에 그대로 찍힌다."""
        for record in self.products + self.overrides:
            lines = list(record.get("hazardStatements") or [])
            lines += [x for items in (record.get("precautionaryStatements") or {}).values() for x in items]
            for line in lines:
                body = re.match(r"^[HP]\d{3}\S*\s(.*)$", line)
                if body:
                    self.assertNotRegex(body.group(1), r"구분\s*[:：]?\s*\d",
                                        f"{record.get('productName') or record.get('productNameCandidate')}: {line[:40]}")

    def test_statements_are_not_letter_spaced_or_split_before_particles(self):
        """"사 용 전 취 급 …" 처럼 한 글자씩 벌어진 문구, "스프레이 의 흡입을" 같은 조사 앞 빈칸이 없어야 한다."""
        for product in self.products:
            lines = list(product.get("hazardStatements") or [])
            lines += [x for items in (product.get("precautionaryStatements") or {}).values() for x in items]
            for line in lines:
                self.assertFalse(N._letter_spaced(line), f"{product['productName']}: {line[:40]}")
                self.assertIsNone(N.PARTICLE_GAP.search(line), f"{product['productName']}: {line[:40]}")

    def test_first_aid_has_no_subsection_titles(self):
        for product in self.products:
            for key, items in (product.get("firstAid") or {}).items():
                for item in items:
                    if T.SENTENCE.search(item):
                        continue
                    self.assertIsNone(re.match(r"^\s*[가-하]\s*[.．]\s*\S", item), f"{product['productName']} {key}: {item[:40]}")
                    self.assertNotIn("물질안전보건자료", item, f"{product['productName']} {key}")

    def test_normalizing_again_changes_nothing(self):
        products, overrides, report = N.normalize_content(self.products, self.overrides)
        self.assertEqual(products, self.products, "문구 꼴을 다시 고치면 또 바뀐다 — build 가 반영하지 않은 상태")
        self.assertEqual(overrides, self.overrides)

    def test_hazard_badge_is_not_published_or_read(self):
        """hazardBadge 는 신호어가 아닌데 신호어로 쓰였다. 데이터와 화면 모두에서 뺐다."""
        for product in self.products:
            self.assertNotIn("hazardBadge", product, product["productName"])
        for name in ("app.js", "label.js", "guide.js"):
            source = (ROOT / "js" / name).read_text(encoding="utf-8")
            self.assertNotIn("product.hazardBadge", source, name)

    def test_repairs_from_pdf_are_in_the_data(self):
        for pid, fix in self.repairs.get("firstAid", {}).items():
            first_aid = self.by_id[pid].get("firstAid") or {}
            for key in fix["fill"]:
                self.assertTrue(first_aid.get(key), f"{self.by_id[pid]['productName']} 응급조치 {key} 가 비었다")
        for pid, fix in self.repairs.get("hazardStatements", {}).items():
            codes = N._codes(self.by_id[pid].get("hazardStatements"))
            self.assertTrue(set(fix["added"]) <= set(codes), self.by_id[pid]["productName"])
        for fix in self.repairs.get("ingredientNames", []):
            row = self.by_id[fix["productId"]]["ingredients"][fix["index"]]
            self.assertEqual(row["chemicalName"], fix["after"], self.by_id[fix["productId"]]["productName"])
        for pid, fix in self.repairs.get("emergencyContact", {}).items():
            self.assertEqual(self.by_id[pid].get("emergencyContact"), fix["after"], self.by_id[pid]["productName"])
        for pid, fix in self.repairs.get("firstAidRemove", {}).items():
            first_aid = self.by_id[pid].get("firstAid") or {}
            for key, items in fix.items():
                for item in items:
                    self.assertNotIn(item, first_aid.get(key) or [], f"{self.by_id[pid]['productName']} 응급조치에 머리글이 남음")
        for pid, fix in self.repairs.get("firstAidText", {}).items():
            first_aid = self.by_id[pid].get("firstAid") or {}
            for key, change in fix.items():
                self.assertEqual([re.sub(r"\s", "", x) for x in first_aid.get(key) or []],
                                 [re.sub(r"\s", "", x) for x in change["after"]],
                                 f"{self.by_id[pid]['productName']} 응급조치 {key} 를 원문대로 잇지 않았다")
        for pid, pairs in self.repairs.get("statementText", {}).items():
            product = self.by_id[pid]
            lines = list(product.get("hazardStatements") or [])
            lines += [x for items in (product.get("precautionaryStatements") or {}).values() for x in items]
            flat = [re.sub(r"\s", "", x) for x in lines]   # 띄어쓰기는 뒤 단계에서 고쳐지므로 빼고 본다
            for pair in pairs:
                self.assertNotIn(re.sub(r"\s", "", pair["before"]), flat, f"{product['productName']}: 잘린 문구가 남음")
                self.assertIn(re.sub(r"\s", "", pair["after"]), flat, f"{product['productName']}: 채운 문구가 없음")

    def test_label_fields_repaired_from_the_source(self):
        """그림문자(원문 그림 확인), 빠진 예방조치문구, 빈 주소·긴급전화가 데이터에 들어 있어야 한다."""
        for pid, fix in self.repairs.get("ghsCodes", {}).items():
            product = self.by_id[pid]
            self.assertEqual(sorted(product.get("ghsCodes") or []), sorted(fix["after"]), product["productName"])
            self.assertEqual(sorted(p["code"] for p in product.get("ghsPictograms") or []), sorted(fix["after"]))
            self.assertIn("verifiedBy", fix, "그림문자는 원문 그림을 보고 확인한 것만 적는다")
        for pid, fix in self.repairs.get("precautionaryStatements", {}).items():
            lines = [x for items in (self.by_id[pid].get("precautionaryStatements") or {}).values() for x in items]
            self.assertTrue(set(fix["added"]) <= set(N._codes(lines)), self.by_id[pid]["productName"])
        for pid, fix in self.repairs.get("supplierAddress", {}).items():
            self.assertEqual(self.by_id[pid].get("supplierAddress"), fix["after"], self.by_id[pid]["productName"])

    def test_candidate_precautions_carry_no_other_section_text(self):
        """추출 후보 예방조치 칸에 6~8항 소항목("나. 환경을 보호하기 위해 …")이 섞이지 않는다."""
        pattern = re.compile(r"^\s*[가-하]\s*[.．]\s*(?:인체를\s*보호|환경을\s*보호|정화\s*또는\s*제거|안전\s*취급|안전한\s*저장)")
        for override in self.overrides:
            for items in (override.get("precautionaryStatements") or {}).values():
                for line in items:
                    self.assertIsNone(pattern.match(line), line[:40])

    def test_emergency_number_is_not_a_piece_of_the_msds_number(self):
        """표지에 찍히는 긴급전화번호 칸에 MSDS 번호 조각이 들어간 적이 있다(오공본드 락카 스프레이)."""
        for product in self.products:
            digits = re.sub(r"\D", "", str(product.get("msdsNo") or ""))
            groups = [re.sub(r"\D", "", g) for g in re.findall(r"\d[\d\s-]{4,}\d", str(product.get("emergencyContact") or ""))]
            if digits and groups:
                self.assertFalse(all(g in digits for g in groups), f"{product['productName']}: {product.get('emergencyContact')}")

    def test_register_dates_are_published_for_the_checked_pdf(self):
        """관리대장에 적은 날짜는 확인한 그 PDF 일 때 사이트에 나간다."""
        for pid, entry in self.register["products"].items():
            product = self.by_id.get(pid)
            if not product or not entry.get("datesCheckedSha256"):
                continue
            digest = hashlib.sha256((ROOT / product["pdfPath"]).read_bytes()).hexdigest()
            self.assertEqual(digest, entry["datesCheckedSha256"], f"{product['productName']}: 날짜 확인 뒤 PDF 가 바뀜")
            for field in ("revisionDate", "issueDate"):
                if entry.get(field):
                    self.assertEqual(product.get(field), entry[field], f"{product['productName']} {field}")

    def test_reprint_flags_follow_the_history(self):
        flagged = {h["newId"] for h in self.register.get("history", []) if h.get("labelReprint")}
        published = {p["id"] for p in self.products if p.get("labelReprint")}
        self.assertEqual(published, flagged & set(self.by_id))
        label = (ROOT / "js" / "label.js").read_text(encoding="utf-8")
        self.assertIn('class="label-reprint no-print"', label, "재인쇄 알림이 표지에 찍히면 안 된다")


class PdfTextRuleTests(unittest.TestCase):
    def test_latest_date_in_a_revision_list_wins(self):
        text = "나. 최초 작성일자 : 2012. 03. 06\n다. 개정횟수 및 최종 개정일자 :\n  16차/2019.01.16, 17차/2019.02.11, 18차/2022.07.13\n라. 기타"
        self.assertEqual(T.revision_date(text), "2022-07-13")
        self.assertEqual(T.issue_date(text), "2012-03-06")

    def test_date_forms(self):
        self.assertEqual(T.first_date("18 3월 2021"), "2021-03-18")
        self.assertEqual(T.first_date("07/Mar/2023"), "2023-03-07")
        self.assertEqual(T.revision_date("2021-12-29 (최종 개정일자) KR - ko 1/28"), "2021-12-29")

    def test_statement_code_before_or_after_text(self):
        hazards, groups = T.parse_statements([
            "유해·위험문구 H280  고압가스 ; 가열 시 폭발할 수 있음",
            "졸음 또는 현기증을 일으킬 수 있음H336",
            "대응 흡입하면 신선한 공기가 있는 곳으로 옮기고 호흡하기 쉬운 자세로 안정을 취하P304+P340",
            "시오.",
            "호흡기 과민성, 구분 1 H334",
        ], set())
        self.assertEqual(hazards, ["H280 고압가스 ; 가열 시 폭발할 수 있음", "H336 졸음 또는 현기증을 일으킬 수 있음"])
        self.assertEqual(groups["response"], ["P304+P340 흡입하면 신선한 공기가 있는 곳으로 옮기고 호흡하기 쉬운 자세로 안정을 취하시오."])

    def test_first_aid_lines_from_another_route_are_dropped(self):
        self.assertEqual(T.usable_first_aid("inhalation", [
            "물질과 접촉시 즉시 20분 이상 흐르는 물에 눈을 씻어내시오.",
            "신선한 공기가 있는 곳으로 옮기시오.",
            "글루콘산 나트륨 527-07-1 0.1 ~ 5",
        ]), ["신선한 공기가 있는 곳으로 옮기시오."])

    def test_english_first_aid_and_corrupted_text(self):
        lines = ["Section 4. First-aid measures", "IF INHALED", "Remove person to fresh air and keep comfortable for breathing.",
                 "IF IN EYES", "Rinse cautiously with water for several minutes.", "4.2 Most important symptoms", "No data available."]
        parsed = T.parse_first_aid(lines, set())
        self.assertEqual(parsed["inhalation"], ["Remove person to fresh air and keep comfortable for breathing."])
        self.assertEqual(parsed["eye"], ["Rinse cautiously with water for several minutes."])
        # 글꼴이 깨진 줄이 섞인 칸은 통째로 두지 않는다
        self.assertEqual(T.usable_first_aid("skin", ["오염된 의복 및 싞발을 벖고 씻으시오.", "즉시 의사의 치료를 받으시오."]), [])
        self.assertEqual(T.usable_first_aid("eye", ["Solvent naphtha (petroleum)", "light arom."]), [])

    def test_address_and_phone_from_section_one(self):
        self.assertEqual(T.supplier_address(["주소 : 서울특별시 마포구 마포대로 4다길 41(마포동) 헨켈타워"]),
                         "서울특별시 마포구 마포대로 4다길 41(마포동) 헨켈타워")
        self.assertEqual(T.supplier_address(["㈜ 에이원케미칼 충남 예산군 봉산면 예덕로 341-10 041-337-6358"]),
                         "충남 예산군 봉산면 예덕로 341-10")
        self.assertEqual(T.emergency_phone(["긴급전화번호 031) 494 - 5096"]), "031-494-5096")

    def test_section_heading_found_out_of_order(self):
        lines = ["4. 응급조치요령", "가. 눈에 들어갔을 때 물로 씻으시오", "2. 유해성·위험성", "분류 없음"]
        self.assertEqual(T.section(lines, 4), lines[:2])
        self.assertEqual(T.section(["제 4 항  응급 조치 요령", "x"], 4)[0], "제 4 항  응급 조치 요령")


class NormalizeRuleTests(unittest.TestCase):
    def test_labels_bullets_and_sentence_tails(self):
        record = {"hazardStatements": ["- H226 인화성 액체 및 증기", "호흡기 과민성, 구분 1 H334", "H334 흡입 시 알레르기성 반응"],
                  "precautionaryStatements": {"prevention": ["예방 P282 : 방한장갑을 착용하시오", "대응 P315 : 즉시 의학적인 조치·조언을",
                                                             "받으시오. P336 : 미지근한 물로 언 부분을 녹이시오"]}}
        N.normalize_statements(record)
        self.assertEqual(record["hazardStatements"], ["H226 인화성 액체 및 증기", "H334 흡입 시 알레르기성 반응"])
        self.assertEqual(record["precautionaryStatements"]["prevention"], ["P282 방한장갑을 착용하시오"])
        self.assertEqual(record["precautionaryStatements"]["response"],
                         ["P315 즉시 의학적인 조치·조언을 받으시오.", "P336 미지근한 물로 언 부분을 녹이시오"])

    def test_spacing_is_borrowed_only_when_the_letters_match(self):
        corpus = N._statement_corpus([{"precautionaryStatements": {"prevention": ["P201 사용 전 취급 설명서를 확보하시오."]}}])
        self.assertEqual(N._fix_spacing("P201 사 용 전 취 급 설 명 서 를 확 보 하 시 오 .", corpus), "P201 사용 전 취급 설명서를 확보하시오.")
        # 빌려 올 문구가 없으면 한 글자 토막만 붙인다. 글자는 그대로.
        self.assertEqual(N._fix_spacing("P405 밀 봉 하 여 저 장 하 시 오 .", {}), "P405 밀봉하여저장하시오.")
        self.assertEqual(N._fix_spacing("P261 분진/흄/가스/미스트/증기/스프레이 의 흡입을 피하시오.", {}),
                         "P261 분진/흄/가스/미스트/증기/스프레이의 흡입을 피하시오.")
        # 보통 글의 "할 수", "및 그", "방지 할 것" 의 한 글자 낱말은 한 글자씩 벌어진 글로 보지 않는다.
        self.assertEqual(N._fix_spacing("H280 가열하면 폭발할 수 있음 및 그 밖의", {}), "H280 가열하면 폭발할 수 있음 및 그 밖의")
        # 동작 명사와 "하다" 사이 빈칸은 떼고, 조사·어미 뒤의 빈칸은 둔다.
        self.assertEqual(N._fix_spacing("폐 흡입을 방지 할 것.", {}), "폐 흡입을 방지할 것.")
        self.assertEqual(N._fix_spacing("인공호흡을 실시 하시오.", {}), "인공호흡을 실시하시오.")
        self.assertEqual(N._fix_spacing("보호조치를 취하도록 하시오", {}), "보호조치를 취하도록 하시오")
        self.assertEqual(N._fix_spacing("적절한 처치를 하시오.", {}), "적절한 처치를 하시오.")
        # 띄어쓰기가 거의 없는 글은 글자가 같은 다른 제품 문구가 있으면 그 띄어쓰기를 빌린다.
        corpus = N._statement_corpus([{"hazardStatements": ["H220 극인화성 가스"]}])
        self.assertEqual(N._fix_spacing("H220 극인화성가스", corpus), "H220 극인화성 가스")

    def test_code_after_text_moves_to_the_front(self):
        record = {"hazardStatements": ["유해·위험문구 · 극인화성 가스 H220"],
                  "precautionaryStatements": {"storage": ["직사광선을 피하고 환기가 잘 되는 곳에 보관하시오P410+P403 ."]}}
        N.normalize_statements(record)
        self.assertTrue(record["hazardStatements"][0].startswith("H220 "), record["hazardStatements"])
        self.assertIn("극인화성 가스", record["hazardStatements"][0])
        self.assertEqual(record["precautionaryStatements"]["storage"], ["P410+P403 직사광선을 피하고 환기가 잘 되는 곳에 보관하시오"])

    def test_ellipsis_after_code_is_kept(self):
        record = {"precautionaryStatements": {"response": ["P321 ... 처치를 하시오."]}}
        N.normalize_statements(record)
        N.normalize_statements(record)
        self.assertEqual(record["precautionaryStatements"]["response"], ["P321 ... 처치를 하시오."])


class SyncArchiveTests(unittest.TestCase):
    def test_archive_folder_is_not_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_구버전 보관(이력)" / "3M").mkdir(parents=True)
            (root / "_구버전 보관(이력)" / "3M" / "old.pdf").write_bytes(b"%PDF-old")
            (root / "3M").mkdir()
            (root / "3M" / "new.pdf").write_bytes(b"%PDF-new")
            self.assertEqual(sorted(sync_pdf_library.scan_pdfs(root)), ["3M/new.pdf"])


if __name__ == "__main__":
    unittest.main()
