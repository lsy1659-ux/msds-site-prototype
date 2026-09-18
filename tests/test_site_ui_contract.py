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
            self.assertIn(f'href="{page}" aria-current="page"', source,
                          f"{page} 가 자기 탭을 지금 보는 화면으로 표시하지 않는다")

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
