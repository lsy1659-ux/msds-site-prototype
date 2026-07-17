import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_source = (ROOT / "js" / "app.js").read_text(encoding="utf-8")

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
