import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = (ROOT / "js" / "app.js").read_text(encoding="utf-8")

    def test_pdf_actions_offer_preview_without_download_or_direct_open(self):
        self.assertIn("function renderPdfPreviewButton", self.app_source)
        self.assertIn("MSDS 미리보기</button>", self.app_source)
        self.assertNotIn("PDF 다운로드", self.app_source)
        self.assertNotIn("원본 PDF 열기", self.app_source)
        self.assertNotIn("data-pdf-full-view", self.app_source)

    def test_automatic_summary_badge_is_not_rendered(self):
        self.assertIn('if (reviewMeta.className === "is-reviewed") return "";', self.app_source)

    def test_mobile_preview_uses_the_internal_full_view(self):
        self.assertIn('window.matchMedia("(max-width: 767px)").matches', self.app_source)
        self.assertIn("startPdfFullView(title, path);", self.app_source)
        self.assertIn('data-pdf-viewer-mode="full"', self.app_source)


if __name__ == "__main__":
    unittest.main()
