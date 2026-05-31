# MSDS Site Prototype

현장 작업자가 QR코드로 접속해 MSDS 핵심 안전정보를 빠르게 확인하는 조회용 프로토타입입니다.

현재는 실제 운영본이 아니라 GitHub에 올려도 안전한 샘플 데이터 기반 화면입니다.

화면은 검색 중심 현장 조회형 UI입니다. 처음부터 전체 제품 목록을 길게 보여주지 않고, 검색어를 입력하거나 분류 버튼을 눌렀을 때 후보 제품을 소형 선택 리스트로 표시합니다.

작업 기준은 먼저 `docs/10_현재_작업상태.md`, `docs/11_운영원칙.md`, `docs/12_다음작업.md` 문서를 확인합니다. 새 Codex 대화에서는 이 문서들을 읽고 이어서 작업합니다.

## 실행 방법

`index.html` 파일을 더블클릭하면 브라우저에서 확인할 수 있습니다.

```text
C:\Users\lsy16\Documents\GitHub\msds-site-prototype\index.html
```

기본 화면은 먼저 `data/msds.local.json`을 읽으려고 시도합니다.

- `data/msds.local.json`이 있으면 로컬 변환 데이터 모드로 표시됩니다.
- `data/msds.local.json`이 없거나 읽기 실패하면 `data/msds-sample.json`을 읽습니다.
- 브라우저 보안 설정 때문에 JSON 읽기가 막히더라도 `js/app.js` 안의 fallback 샘플 데이터로 기본 화면과 검색 기능이 동작하도록 구성되어 있습니다.

## 엑셀을 JSON으로 변환하는 방법

실제 엑셀 원본은 `data/raw/` 폴더에 넣고 사용합니다.

```text
data/raw/MSDS_통합대장_누적3.xlsx
```

필요한 Python 패키지를 설치합니다.

```bash
pip install -r requirements.txt
```

아래 명령으로 엑셀을 홈페이지 검색용 JSON으로 변환합니다.

```bash
python scripts/convert_excel_to_json.py --input data/raw/MSDS_통합대장_누적3.xlsx --output data/msds.local.json
```

기본 시트명은 `통합종합_보기용`, 기본 헤더 행은 `3행`입니다.

시트명이나 헤더 행이 다르면 아래처럼 지정할 수 있습니다.

```bash
python scripts/convert_excel_to_json.py --input data/raw/MSDS_통합대장_누적3.xlsx --output data/msds.local.json --sheet 통합종합_보기용 --header-row 3
```

## PDF 연결 검사 방법

실제 PDF 파일은 저장소에 올리지 않고, 로컬 PC의 `pdf/` 폴더에만 넣고 검사합니다.

```bash
python scripts/check_pdf_links.py --data data/msds.local.json --pdf-dir pdf
```

이 검사는 엑셀의 파일명과 PDF 파일명이 정확히 같은 경우뿐 아니라, 정규화한 파일명과 PDF 내부 텍스트도 함께 확인합니다. PDF 파일명이 엑셀 파일명과 달라도 PDF 내부의 제품명, 물질명, CAS No.가 엑셀 데이터와 같으면 연결 후보로 볼 수 있습니다.

다만 PDF 내부 텍스트 기반 매칭은 오탐 가능성이 있으므로 자동 확정하지 않고 확인 필요 대상으로 분류합니다. 스캔본 PDF처럼 텍스트 추출이 되지 않는 파일도 `text_extract_failed`, `scanned_pdf_or_image_pdf`, `manual_review_required` 상태로 보고 사람이 확인할 수 있게 합니다.

같은 PDF가 파일명만 다르게 중복 저장된 경우도 검사 대상입니다. 중복 또는 유사 매칭 결과는 삭제, 이름 변경, 이동 없이 리포트로만 제공합니다.

검사 결과는 아래 로컬 리포트로 저장됩니다.

```text
reports/pdf-link-report.local.json
reports/pdf-link-report.local.csv
```

이 리포트에는 실제 제품명이나 PDF 정보가 들어갈 수 있으므로 GitHub에 올리지 않습니다.

## PDF 요약 후보 추출 방법

PDF 원문에서 좌측 현장 요약판에 넣을 후보 정보를 뽑을 때는 아래 스크립트를 사용합니다.

```bash
python scripts/extract_pdf_summary.py --input pdf/PN3021.pdf --output data/msds-overrides.local.json
```

이 결과는 자동 확정값이 아니라 `검토필요` 상태의 후보입니다. 사람이 확인하기 전까지 좌측 요약판의 확정 정보처럼 사용하지 않습니다.

샘플 구조는 아래 파일에서 확인할 수 있습니다.

```text
data/msds-overrides.sample.json
```

실제 PDF에서 추출한 결과인 `data/msds-overrides.local.json`은 실제 제품정보가 들어갈 수 있으므로 GitHub에 올리지 않습니다.

## 주의사항

- 실제 회사 엑셀 원본은 이 저장소에 넣지 않습니다.
- 실제 MSDS PDF 파일은 이 저장소에 넣지 않습니다.
- 실제 내부자료, 거래처 자료, 운영 데이터는 GitHub에 올리지 않습니다.
- 실제 엑셀 원본은 로컬 PC의 `data/raw/`에만 둡니다.
- 변환 결과인 `data/msds.local.json`도 GitHub에 올리지 않습니다.
- PDF 요약 후보 파일인 `data/msds-overrides.local.json`도 GitHub에 올리지 않습니다.
- 현재 `pdf/` 폴더에는 샘플 단계 안내 문서만 두며, 실제 PDF는 포함하지 않습니다.

나중에 실제 PDF를 연결할 때는 `pdf/` 폴더에 파일을 넣고, 샘플 데이터의 `fileName` 또는 `pdfPath`와 맞춰 관리합니다.

현재 `.gitignore` 설정으로 엑셀 파일, PDF 파일, `data/raw/`, `data/original/`, `data/msds.local.json`, `data/*.local.json`은 GitHub에 올라가지 않도록 제외되어 있습니다.

## 디자인 수정 위치

화면 디자인은 주로 아래 파일에서 수정합니다.

```text
css/style.css
```

CSS 상단의 변수 영역에서 색상, 테두리, 여백, 글자 크기를 조정할 수 있습니다.

좌측 현장 요약판, 검색 영역, 우측 상세패널은 CSS 주석으로 구분되어 있어 나중에 `A4 안내문 스타일`, `카드형 스타일`, `모바일 간편조회 스타일`로 바꾸기 쉽게 정리되어 있습니다.
