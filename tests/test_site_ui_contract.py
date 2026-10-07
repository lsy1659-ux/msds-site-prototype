import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# 위쪽 탭 줄에 있어야 할 화면과 그 차례. 화면마다 손으로 넣는 곳이라
# 하나를 더하면 나머지에 빠뜨리기 쉽다.
TAB_PAGES = ("index.html", "label.html", "guide.html", "substance.html")
TAB_LABELS = ["조회", "경고표지", "관리요령", "물질", "오프라인 저장"]


class SiteUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = (ROOT / "js" / "app.js").read_text(encoding="utf-8")

    def test_every_page_carries_the_same_tab_strip(self):
        for page in TAB_PAGES:
            source = (ROOT / page).read_text(encoding="utf-8")
            strip = re.search(r'<div class="top-bar-tabs">(.*?)</div>', source, re.S)
            self.assertIsNotNone(strip, f"{page} 에 탭 줄이 없다")
            labels = re.findall(r'class="top-bar-tab"[^>]*>\s*([^<]+?)\s*<', strip.group(1))
            self.assertEqual(labels, TAB_LABELS, f"{page} 의 탭이 다르다")

    def test_pages_mark_their_own_tab_as_current(self):
        for page in TAB_PAGES:
            source = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn(f'href="{page}"', source)
            self.assertIn('aria-current="page"', source,
                          f"{page} 가 자기 탭을 지금 보는 화면으로 표시하지 않는다")

    def test_substance_tab_stays_behind_the_admin_gate(self):
        for page in TAB_PAGES:
            source = (ROOT / page).read_text(encoding="utf-8")
            tab = re.search(r'<a class="top-bar-tab" href="substance\.html"[^>]*>', source)
            self.assertIsNotNone(tab, f"{page} 에 물질 탭이 없다")
            self.assertIn("data-admin-only", tab.group(0),
                          f"{page} 의 물질 탭이 관리자 모드 밖에서도 보인다")
            # 자바스크립트가 켜기 전에 이미 감춰져 있어야 탭이 번쩍이지 않는다.
            self.assertIn("msds.admin.v1", source,
                          f"{page} 가 첫 그림 전에 관리자 상태를 정하지 않는다")

    def test_substance_page_hides_its_body_until_unlocked(self):
        for page in ("substance.html", "register.html"):
            source = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn('class="admin-locked-screen" data-admin-locked', source, page)
            self.assertIn('<main class="substance-main" data-admin-only>', source, page)
            self.assertIn('id="adminGate"', source, page)

    def test_admin_gate_never_spells_the_passcode_out(self):
        """암호를 주석이나 문자열로 적어 두면 가림막 구실조차 못 한다.

        저장소가 공개라 적는 순간 누구나 읽는다. 실제로 한 번 저질렀던
        실수라서, 파일 안의 낱말을 모두 해시해 보고 PASS_HASH 와 같은
        것이 있으면 잡는다.
        """
        source = (ROOT / "js" / "admin-gate.js").read_text(encoding="utf-8")
        stored = re.search(r'const PASS_HASH = "([0-9a-f]{64})"', source)
        self.assertIsNotNone(stored, "PASS_HASH 줄이 없다")

        for token in set(re.findall(r"[^\s\"'`()\[\]{},;]+", source)):
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            self.assertNotEqual(digest, stored.group(1),
                                f"암호가 파일에 그대로 적혀 있다: {token!r}")

    def test_guide_emergency_slots_only_take_matching_sentences(self):
        """관리요령의 누출 시·화재 시 칸에 엉뚱한 문장이 들어가지 않는다.

        낱말 하나로 대응 문구를 고르는데, 한 글자 낱말은 다른 말 속에
        숨어 걸린다. "불" 이 "불편함을 느끼면" 에 걸려 50장의 화재 시 칸에
        의사 진찰 문구가 들어간 적이 있다. guide.js 의 낱말 목록을 그대로
        읽어 실제 데이터에 대 보고, 걸린 문장이 그 사고와 관련 있는지 본다.
        """
        guide = (ROOT / "js" / "guide.js").read_text(encoding="utf-8")
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))

        def words(name):
            found = re.search(rf"const {name} = \[(.*?)\];", guide, re.S)
            self.assertIsNotNone(found, f"guide.js 에 {name} 가 없다")
            return re.findall(r'"([^"]+)"', found.group(1))

        # 걸려서는 안 되는 말. 겉보기에 낱말을 품고 있지만 그 사고와는 무관하다.
        not_this = {"FIRE_WORDS": ["불편"], "SPILL_WORDS": []}

        for name, bad in not_this.items():
            keys = words(name)
            for word in keys:
                self.assertGreaterEqual(len(word), 2, f"{name} 의 '{word}' 는 너무 짧아 다른 말에 걸린다")
            for product in products:
                response = (product.get("precautionaryStatements") or {}).get("response") or []
                hit = next((text for text in response if any(word in text for word in keys)), None)
                if hit:
                    for wrong in bad:
                        self.assertNotIn(wrong, hit,
                                         f"{product['productName']} 의 {name} 칸에 무관한 문장: {hit[:40]}")

    def test_signal_word_never_comes_from_hazard_badge(self):
        """신호어를 hazardBadge 에서 가져오지 않는다.

        hazardBadge 는 신호어가 아니라 228건 중 180건에 일괄로 "위험"이 들어간
        칸이었다. 경고표지·관리요령이 이걸 신호어로 써서 원문 "경고" 18건이
        "위험"으로, 원문 "위험" 14건이 빈칸으로 인쇄됐다.
        """
        for name in ("label.js", "guide.js"):
            source = (ROOT / "js" / name).read_text(encoding="utf-8")
            code = "\n".join(line for line in source.splitlines() if not line.strip().startswith("//"))
            self.assertNotRegex(code, r"(signal|badge)\s*=\s*String\(product\.hazardBadge",
                                f"{name} 가 hazardBadge 를 신호어로 쓴다")
            self.assertIn("product.signalWord", source, f"{name} 가 signalWord 를 쓰지 않는다")
        self.assertIn("function resolveSignalWord(product)", self.app_source)
        self.assertNotIn("cleanSignalWord(product.hazardBadge)", self.app_source)

    def test_public_signal_words_match_the_register(self):
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        register = json.loads((ROOT / "data" / "msds-register.json").read_text(encoding="utf-8"))["products"]
        for product in products:
            entry = register[product["id"]]
            expected = "해당없음" if entry.get("notClassified") else entry.get("signalWord", "")
            if expected:
                self.assertEqual(product.get("signalWord"), expected, product["productName"])

    def test_not_classified_products_carry_no_hazard_marks(self):
        """원문이 분류기준 비해당이라고 적은 제품에 그림문자가 남으면 표지에 인쇄된다."""
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        overrides = json.loads((ROOT / "data" / "msds-overrides.public.json").read_text(encoding="utf-8"))
        register = json.loads((ROOT / "data" / "msds-register.json").read_text(encoding="utf-8"))["products"]
        files = {}
        for o in overrides:
            for key in ((o.get("match") or {}).get("fileName"), str(o.get("sourcePdfPath", "")).split("/")[-1]):
                if key:
                    files.setdefault(key, o)
        for product in products:
            if not register[product["id"]].get("notClassified"):
                continue
            self.assertTrue(product.get("hazardNotClassified"), product["productName"])
            for field in ("ghsPictograms", "hazardStatements", "ghsCodes"):
                self.assertEqual(product.get(field) or [], [], f"{product['productName']} {field}")
            override = files.get(product.get("fileName")) or {}
            for field in ("ghsPictograms", "labelGhsPictograms", "hazardStatements"):
                self.assertEqual(override.get(field) or [], [], f"{product['productName']} override {field}")

    def test_every_product_is_in_the_register_and_numbers_are_clean(self):
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        register = json.loads((ROOT / "data" / "msds-register.json").read_text(encoding="utf-8"))
        entries = register["products"]
        for product in products:
            self.assertIn(product["id"], entries, f"관리대장에 없음: {product['productName']}")
            number = product.get("msdsNo") or ""
            if number:
                self.assertRegex(number, r"^[A-Z]{2}\d{5}-\d{10}$", product["productName"])
            self.assertNotEqual(entries[product["id"]]["status"], "retired", product["productName"])
        for pid, entry in entries.items():
            if entry["status"] in ("not_required", "submission_exempt"):
                self.assertTrue(entry.get("basis"), f"근거 없는 '필요 없음': {entry.get('productName')}")

    def test_retired_ids_still_open_their_successor(self):
        """구판을 목록에서 빼도 그 판으로 뽑은 표지의 QR 은 새 판으로 열린다."""
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        register = json.loads((ROOT / "data" / "msds-register.json").read_text(encoding="utf-8"))["products"]
        former = {old: p["id"] for p in products for old in p.get("formerIds", [])}
        for pid, entry in register.items():
            if entry["status"] == "retired" and entry.get("replacedBy"):
                self.assertEqual(former.get(pid), entry["replacedBy"], entry.get("productName"))
        self.assertIn("(product.formerIds || []).includes(requestedId)", self.app_source)

    def test_replacement_history_matches_the_register(self):
        """최신판으로 바꾼 이력은 관리대장의 구판·새 판과 맞아야 한다.

        이력만 적고 구판을 retired 로 안 두면 두 판이 같이 목록에 뜨고,
        반대로 구판만 빼고 이력이 없으면 무엇이 바뀌었는지 알 길이 없다.
        """
        products = {p["id"]: p for p in json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))}
        register = json.loads((ROOT / "data" / "msds-register.json").read_text(encoding="utf-8"))
        entries = register["products"]
        replaced = set()
        for item in register.get("history", []):
            for field in ("date", "action", "productName", "oldId", "newId"):
                self.assertTrue(item.get(field), f"이력에 {field} 가 없다: {item}")
            self.assertIn(item["newId"], products, f"이력의 새 판이 목록에 없다: {item['productName']}")
            if item["oldId"] != item["newId"]:
                replaced.add(item["oldId"])
                self.assertEqual(entries[item["oldId"]]["status"], "retired", item["productName"])
                self.assertEqual(entries[item["oldId"]].get("replacedBy"), item["newId"], item["productName"])
            number = item.get("newMsdsNo") or ""
            if number:
                self.assertEqual(products[item["newId"]].get("msdsNo"), number, item["productName"])
        for pid, entry in entries.items():
            if entry.get("kind") == "구판(최신판으로 교체)":
                self.assertIn(pid, replaced, f"교체 이력이 없는 구판: {entry.get('productName')}")

    def test_admin_gate_is_documented_as_a_curtain_not_a_lock(self):
        # 정적 사이트라 암호 확인이 브라우저에서 일어난다. 이 파일을 나중에
        # 고치는 사람이 진짜 잠금으로 오해하면 민감한 것을 뒤에 둘 수 있다.
        source = (ROOT / "js" / "admin-gate.js").read_text(encoding="utf-8")
        self.assertIn("잠금이 아니라 가림막", source)

    def test_pdf_actions_keep_view_controls_without_download(self):
        self.assertIn("function renderOriginalPdfButton", self.app_source)
        self.assertIn("function renderPdfPreviewButton", self.app_source)
        self.assertIn("원본 PDF 열기</button>", self.app_source)
        self.assertIn("PDF 미리보기</button>", self.app_source)
        self.assertIn("전체화면 미리보기</button>", self.app_source)
        self.assertNotIn("PDF 다운로드", self.app_source)
        self.assertNotIn(" download", self.app_source)
        self.assertNotIn('target="_blank"', self.app_source)

    def test_automatic_summary_badge_is_not_rendered(self):
        self.assertIn('if (reviewMeta.className === "is-reviewed") return "";', self.app_source)

    def test_mobile_preview_uses_the_internal_pdf_viewer(self):
        self.assertIn("startPdfPreview(title, path);", self.app_source)
        self.assertIn('data-pdfjs-preview-mount', self.app_source)
        self.assertIn('data-pdf-viewer-mode="full"', self.app_source)

    # ── 2026-10-07 GPT 점검 반영 ──────────────────────────────

    def _ppe_rules(self):
        """js/ppe-rules.js 의 낱말 목록을 그대로 읽어 파이썬으로 같은 판별을 한다."""
        source = (ROOT / "js" / "ppe-rules.js").read_text(encoding="utf-8")
        rules = re.findall(r'key: "(\w+)",.*?words: \[(.*?)\]', source, re.S)
        self.assertEqual([key for key, _ in rules], ["goggles", "gloves", "mask", "suit", "boots"])
        fire = re.search(r"const FIRE_CONTEXT = \[(.*?)\];", source, re.S)
        self.assertIsNotNone(fire)
        return (
            {key: re.findall(r'"([^"]+)"', words) for key, words in rules},
            re.findall(r'"([^"]+)"', fire.group(1)),
        )

    def _detect_ppe(self, texts):
        rules, fire = self._ppe_rules()
        sentences = [part.strip() for text in texts
                     for part in re.split(r"[.。!?;]\s*|\n+|\s(?=[가-하]\.)", text or "") if part.strip()]
        lines = [t for t in sentences if not any(w in re.sub(r"\s+", "", t.lower()) for w in fire)]
        joined = re.sub(r"\s+", "", " ".join(lines).lower())
        return [key for key, words in rules.items() if any(w in joined for w in words)]

    def test_ppe_words_are_names_of_equipment_not_single_syllables(self):
        """"눈"·"호흡"·"신체" 한 낱말로 고르면 응급조치 문장에도 보호구가 붙는다."""
        rules, _ = self._ppe_rules()
        banned = {"눈", "호흡", "신체", "보호화", "송기", "눈보호", "신체보호"}
        for key, words in rules.items():
            self.assertFalse(banned & set(words), f"{key} 에 너무 넓은 낱말: {banned & set(words)}")

    def test_unknown_ppe_text_never_gets_a_default_pictogram(self):
        """종류를 못 읽은 문구에 보호복 그림을 기본으로 붙이지 않는다."""
        self.assertNotIn('const file = labels[type] ? type : "suit"', self.app_source)
        self.assertNotIn("function getPpeType(", self.app_source)
        self.assertIn("window.MsdsPpe.detect(sources)", self.app_source)
        guide = (ROOT / "js" / "guide.js").read_text(encoding="utf-8")
        self.assertIn("window.MsdsPpe.detect(", guide)
        self.assertNotIn("const PPE_RULES", guide)

    def test_tc317_shows_all_four_ppe_from_one_p280_sentence(self):
        """P280 한 문장에 든 보호구를 모두 읽는다. 전에는 보안경 하나가 되어 보호장갑이 빠졌다."""
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        product = next(p for p in products if p["id"] == "msds-033")
        found = self._detect_ppe([product.get("ppeSummary", ""), *product.get("ppeCandidates", [])])
        self.assertEqual(found, ["goggles", "gloves", "mask", "suit"])
        # 제목 조각과 화재 진압용 보호구만으로는 아무것도 그리지 않는다.
        self.assertEqual(self._detect_ppe(["○ 착용할 보호구 :", "다. 화재진압 시 착용할 보호구 및 예방조치"]), [])
        self.assertEqual(self._detect_ppe(["소방관은 공기호흡기(SCBA)를 착용할 것"]), [])
        self.assertEqual(self._detect_ppe(["흡입하면 호흡하기 쉬운 자세로 안정을 취하시오"]), [])
        # 8항이 한 덩어리로 들어와 "화재" 가 섞여 있어도 착용 문장은 살린다(GHP 제품).
        self.assertEqual(self._detect_ppe(["가.화재 시 소화기를 쓴다.나.호흡기 보호 :연속 작업시 방독면 등을 착용한다."]), ["mask"])

    def test_print_buttons_do_not_print_everything_when_nothing_is_picked(self):
        for page, script, prefix in (("guide.html", "guide.js", "guide"), ("label.html", "label.js", "label")):
            html = (ROOT / page).read_text(encoding="utf-8")
            button = re.search(rf'<button[^>]*id="{prefix}Print"[^>]*>', html)
            self.assertIsNotNone(button, page)
            self.assertIn("disabled", button.group(0), f"{page} 의 고른 것 인쇄 단추가 처음부터 눌린다")
            self.assertIn(f'id="{prefix}PrintAll"', html, f"{page} 에 전체 인쇄 단추가 따로 없다")
            source = (ROOT / "js" / script).read_text(encoding="utf-8")
            self.assertIn("if (!picked) return;", source, f"{script} 가 고른 것 없이 인쇄한다")
            self.assertIn("window.confirm(", source, f"{script} 가 전체 인쇄 전에 묻지 않는다")

    def test_selected_product_follows_across_tabs(self):
        for page in ("index.html", "label.html", "guide.html"):
            html = (ROOT / page).read_text(encoding="utf-8")
            self.assertIn('src="js/handoff.js', html, f"{page} 에 handoff.js 가 없다")
        self.assertIn("window.MsdsHandoff?.carry(", self.app_source)
        for script in ("label.js", "guide.js"):
            source = (ROOT / "js" / script).read_text(encoding="utf-8")
            self.assertIn("window.MsdsHandoff?.carry(", source, script)
            self.assertIn("window.MsdsHandoff?.requested()", source, script)

    def test_pdf_refits_when_the_screen_size_changes(self):
        self.assertIn('window.addEventListener("resize", schedulePdfRefit', self.app_source)
        self.assertIn('window.addEventListener("orientationchange", schedulePdfRefit', self.app_source)
        self.assertIn("data-pdf-page-input", self.app_source)
        self.assertIn("data-pdf-search-form", self.app_source)

    def test_service_worker_only_clears_msds_caches(self):
        source = (ROOT / "sw.js").read_text(encoding="utf-8")
        activate = source[source.index('addEventListener("activate"'):source.index("function isDataRequest")]
        self.assertIn('name.startsWith("msds-")', activate, "다른 사이트의 저장칸까지 지운다")
        self.assertIn('name.startsWith("msds-") && name.endsWith("-pdf")', self.app_source)

    def test_every_local_script_and_style_is_saved_for_offline(self):
        """화면이 읽는 js·css 가 서비스워커 목록에 없으면 끊긴 현장에서 화면이 깨진다."""
        source = (ROOT / "sw.js").read_text(encoding="utf-8")
        shell = set(re.findall(r'"([^"]+)"', source[source.index("const SHELL_ASSETS"):source.index("const DATA_ASSETS")]))
        for page in ("index.html", "label.html", "guide.html", "substance.html", "register.html"):
            html = (ROOT / page).read_text(encoding="utf-8")
            for asset in re.findall(r'(?:src|href)="((?:js|css|vendor)/[^"?]+)', html):
                self.assertIn(asset, shell, f"{page} 의 {asset} 가 오프라인 저장 목록에 없다")

    def test_tone_layer_is_the_last_stylesheet_on_every_page(self):
        """css/tone.css 가 위에서 덮는 층이라 맨 뒤에 와야 한다."""
        for page in ("index.html", "label.html", "guide.html", "substance.html", "register.html"):
            html = (ROOT / page).read_text(encoding="utf-8")
            sheets = re.findall(r'<link rel="stylesheet" href="(css/[^"?]+)', html)
            self.assertEqual(sheets[-1], "css/tone.css", f"{page} 의 마지막 스타일이 tone.css 가 아니다")

    def test_ghs_and_ppe_signs_are_not_restyled_as_icons(self):
        """GHS 그림문자와 ISO 7010 표지는 원본 그림 그대로 둔다. 화면 아이콘으로 바꾸지 않는다."""
        icons = (ROOT / "js" / "ui-icons.js").read_text(encoding="utf-8")
        names = re.findall(r"^\s{4}(\w+): '", icons, re.M)
        self.assertTrue(names, "ui-icons.js 의 아이콘 이름을 못 읽었다")
        self.assertFalse([name for name in names if name.startswith(("ghs", "ppe"))], "표지를 화면 아이콘으로 바꿨다")
        tone = (ROOT / "css" / "tone.css").read_text(encoding="utf-8")
        self.assertNotRegex(tone, r"\.ghs-diamond[^{]*\{[^}]*(filter|background)", "그림문자 그림을 칠한다")
        self.assertNotRegex(tone, r"\.ppe-sign img[^{]*\{[^}]*filter", "보호구 표지 그림을 칠한다")


if __name__ == "__main__":
    unittest.main()
