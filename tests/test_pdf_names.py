"""원본 PDF 파일 이름 규칙: 회사명_제품명_MSDS_날짜.pdf (2026-10-14)."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pdf_names as N  # noqa: E402

PATTERN = re.compile(r"^[^_/]+_.+_MSDS_(\d{8}|날짜없음)( \(\d+\))?\.pdf$")


class PdfNameRuleTests(unittest.TestCase):
    def test_short_company_names(self):
        self.assertEqual(N.short_company("(주)노루오토코팅"), "NAC")
        self.assertEqual(N.short_company("KNK코팅스"), "KNK")
        self.assertEqual(N.short_company("케이씨씨 울산공장"), "KCC")
        self.assertEqual(N.short_company("한국쓰리엠"), "3M")
        # 공급사 표기가 깨졌으면 보관함 폴더 이름으로
        self.assertEqual(N.short_company("Produc", "00_ 사출\\그레이코(GRACO)"), "GRACO")
        # 공급사 표기가 먼저다(폴더 '나바켐, 남방CNA' 의 남방CNA 제품)
        self.assertEqual(N.short_company("남방CNA", "00_ 사출\\나바켐(NAVAKEM), 남방CNA(주)"), "남방CNA")

    def test_date_falls_back_to_issue_date(self):
        self.assertEqual(N.file_date({"revisionDate": "2025-06-19", "issueDate": "2019-03-21"}), "20250619")
        self.assertEqual(N.file_date({"revisionDate": "", "issueDate": "2019-03-21"}), "20190321")
        self.assertEqual(N.file_date({}), "날짜없음")

    def test_standard_name(self):
        product = {"supplier": "노루오토코팅", "productName": "DR-174 SWP M/BASE (SP2,SK3-CAR)", "revisionDate": "2023-05-10"}
        self.assertEqual(N.standard_name(product), "NAC_DR-174 SWP M-BASE (SP2,SK3-CAR)_MSDS_20230510.pdf")
        # 제품명이 회사명으로 시작하면 한 번만
        self.assertEqual(N.standard_name({"supplier": "한국쓰리엠", "productName": "3M PN3021 컴파운드", "revisionDate": "2026-07-26"}),
                         "3M_PN3021 컴파운드_MSDS_20260726.pdf")

    def test_every_site_pdf_follows_the_rule(self):
        products = json.loads((ROOT / "data" / "msds.public.json").read_text(encoding="utf-8"))
        bad = [p["fileName"] for p in products if not PATTERN.match(p.get("fileName") or "")]
        self.assertEqual(bad, [], "새 PDF 는 회사명_제품명_MSDS_날짜.pdf 로 이름을 바꿔 등록한다(scripts/pdf_names.py)")

    def test_renames_lead_to_existing_files(self):
        renames = json.loads((ROOT / "data" / "pdf-renames.json").read_text(encoding="utf-8"))["renames"]
        missing = [new for new in renames.values() if not (ROOT / new).exists()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
