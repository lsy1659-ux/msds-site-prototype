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
        source = (ROOT / "substance.html").read_text(encoding="utf-8")
        self.assertIn('class="admin-locked-screen" data-admin-locked', source)
        self.assertIn('<main class="substance-main" data-admin-only>', source)
        self.assertIn('id="adminGate"', source)

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


if __name__ == "__main__":
    unittest.main()
