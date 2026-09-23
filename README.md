# MSDS Site Prototype

현장 작업자가 QR코드로 접속해 MSDS 핵심 안전정보를 빠르게 확인하는 조회용 프로토타입입니다.

현재 상태는 GitHub Pages 실제 MSDS PDF 미리보기 공개 운영 완료입니다. 공개 URL은 <https://lsy1659-ux.github.io/msds-site-prototype/> 이며, 공개 화면은 `data/msds.public.json`, `data/msds-overrides.public.json`, `pdf/` 폴더의 대표 PDF 224개를 사용해 실제 제품 검색, 상세정보 표시, 사이트 내부 전체 페이지 PDF 미리보기를 제공합니다. 로컬 실행 화면은 `data/msds.local.json`, `data/msds-overrides.local.json`이 있으면 그 파일을 우선 사용합니다.

공개 운영 확인 결과 `data/msds.public.json`과 `data/msds-overrides.public.json` 접근은 정상이고, `data/msds.local.json`, `data/msds-overrides.local.json`, `reports/*.local.*` 파일은 공개 URL에서 404로 비공개 상태를 유지합니다. 실제 엑셀, `data/raw/`, `data/original/`, `.env`도 계속 GitHub에 올리지 않습니다.

화면은 검색 중심 현장 조회형 UI입니다. 처음부터 전체 제품 목록을 길게 보여주지 않고, 검색어를 입력하거나 분류 버튼을 눌렀을 때 후보 제품을 소형 선택 리스트로 표시합니다.

좁은 화면과 모바일에서는 검색 영역, 제품 선택, 현장 요약판, 상세정보, 성분정보, 작업자 주의 포인트, PDF 미리보기 순서의 1열 흐름으로 표시됩니다. 넓은 PC 화면에서는 현장 요약판과 상세정보가 2단으로 배치됩니다.

작업자 주의 포인트는 브라우저 안의 로컬 규칙으로만 정리합니다. 사이트 사용 중 OpenAI 또는 외부 AI API를 호출하지 않으며, 별도 API 토큰도 사용하지 않습니다.

운영 문서는 공개 저장소에 두지 않고 회사 OneDrive의 `00_바탕 화면\10_ 안전·보건·소방\02_보건\01_ MSDS\MSDS 사이트 운영문서` 폴더에서 관리합니다. 작업 기준은 먼저 그 폴더의 `10_현재_작업상태.md`, `11_운영원칙.md`, `12_다음작업.md`를 확인합니다. 새 Codex 대화에서도 이 문서들을 읽고 이어서 작업합니다.

## 화면 구성

위쪽 탭으로 다섯 화면을 오갑니다. 탭 markup 은 화면마다 손으로 들어가 있어서,
`tests/test_site_ui_contract.py` 가 네 화면의 탭이 같은지 확인합니다.

| 화면 | 파일 | 하는 일 |
| --- | --- | --- |
| 조회 | `index.html` | 제품에서 시작합니다. 검색, 요약, 성분표, PDF 원문. `목록 CSV` 로 지금 걸러진 제품을 내보냅니다. |
| 경고표지 | `label.html` | 용기에 붙일 GHS 경고표지를 인쇄합니다. |
| 관리요령 | `guide.html` | 시행규칙 제168조 작업공정별 관리요령을 인쇄합니다. |
| 물질 | `substance.html` | 성분에서 시작합니다. CAS 로 묶어 어느 물질이 어느 제품에 들어 있는지 봅니다. **관리자 모드에서만 보입니다.** |
| MSDS 번호 관리대장 | `register.html` | 제품마다 MSDS 번호가 있어야 하는지, 없어도 되는지, 무엇을 더 받아야 하는지 봅니다. **관리자 패널에서 엽니다.** |
| 오프라인 저장 | `index.html?offline=1` | 서비스워커로 화면과 PDF 를 받아 둡니다. |

### MSDS 번호 관리대장

`data/msds-register.json` 이 제품마다 MSDS 번호의 **상태**를 정합니다. 2026-09-23 전수조사로 만들었고, 사람이 고치는 곳은 이 파일 하나입니다.

| status | 뜻 | 번호 |
| --- | --- | --- |
| `verified` | 사이트 번호 = 원본 PDF 번호 | 있음 |
| `required` | 유해성 분류가 있는 산업용 제품인데 가진 MSDS 에 번호가 없음. 공급사에 번호 기재본 요청 | 없음 |
| `not_required` | 원문이 분류기준 비해당이거나 다른 법률로 관리되는 제품. 까닭과 근거가 필수 | 없음 |
| `submission_exempt` | 시험용 시약. MSDS 게시·비치는 필요하지만 공단 제출(번호)만 면제 | 없음 |
| `pending` | 원문만으로 판단 불가. 라벨·용도·수입자 자료 확인 필요 | 있거나 없음 |
| `retired` | 구판·중복. 목록에서 빼고 `replacedBy` 의 새 판으로 이어짐 | — |

판정 기준은 번호가 있느냐가 아니라 **원문 제2항의 유해성 분류**입니다. 유해성 분류가 있는 산업용 제품은
2026. 1. 16. 로 제출 유예가 모두 끝나(법률 제16272호 부칙 제7조·제8조, 시행규칙 부칙 제9조·제10조) 번호가 적힌
MSDS 를 받아야 합니다(시행규칙 제160조제1항). 번호가 있다고 의무 대상인 것도 아닙니다 — 현대EP 는 비유해 PP 수지도
제출해 번호를 받았습니다.

**왜 따로 두는가.** 공개 데이터는 집 PC 가 로컬 데이터로 다시 만듭니다. 공개 데이터를 직접 고치면 다음 빌드 때
되돌아갑니다. 그래서 `scripts/build_public_data.py` 가 끝에 `scripts/apply_msds_register.py` 를 불러 관리대장을
덮어씁니다. 관리대장이 정하는 것은 다음과 같습니다.

- **번호**: `msdsNo` 에는 공단 번호만 둡니다. 'MSDS번호 미기재'·'제품명기준-…' 같은 자리표시는 지우고,
  LB2982·문서그룹 42-2264-2 같은 공급사 문서번호는 `supplierDocNo` 로 옮깁니다.
- **신호어**: `scripts/extract_signal_words.py` 가 원문 제2항에서 뽑은 값. 경고표지·관리요령·조회 화면이 모두
  `signalWord` 하나만 씁니다. `hazardBadge` 는 신호어가 아닙니다(228건 중 180건에 일괄 "위험").
- **비해당**: `notClassified` 인 제품은 그림문자·유해위험문구·예방조치문구를 비웁니다(overrides 쪽도).
- **구판**: `retired` 는 목록에서 빼고 새 판에 `formerIds` 를 남겨 옛 QR 이 새 판을 엽니다. 옛 PDF 는 기록으로 둡니다.
- **날짜**: `revisionDate`·`issueDate` 를 적으면 그 값으로 바꿉니다. 원문과 다르게 들어간 개정일을 바로잡을 때만 씁니다.
- **이력**: `history` 에 최신판 교체·번호 확인을 한 줄씩 남깁니다(날짜, 이전/새 번호·개정일·파일, 출처, SHA-256).
  관리대장 화면의 "교체·확인 이력"에 보이고 CSV 로 받을 수 있습니다.
- **성분표**: 2026-09-18 원본 대조로 고친 113행(`reports/ingredient_repair_log.json`)도 다시 반영합니다.

**새 제품을 등록할 때**는 관리대장에도 한 줄을 넣습니다. 빠지면 `validate_public_release.py` 가
`MSDS_REGISTER_ENTRY_MISSING` 경고를 냅니다. '필요 없음'·'제출 면제'를 근거 없이 넣으면 오류입니다.

```
py scripts/extract_signal_words.py --write    신호어를 원문에서 다시 뽑아 관리대장에 적기
py scripts/apply_msds_register.py --write     관리대장을 사이트 데이터에 반영
```

**최신판으로 바꿀 때**는 새 PDF 를 같은 폴더에 `제품명_MSDS_YYYYMMDD.pdf` 로 넣고 새 제품으로 등록한 뒤,
구판 항목을 `retired`·`replacedBy` 로 두고 `history` 에 한 줄 남깁니다. 원본 보관함(OneDrive `00_ 캠스 MSDS`)에서는
구판을 지우지 않고 `_구버전 보관(이력)\같은 하위 경로` 로 옮기고, 보관함 맨 위 `MSDS_교체이력.csv` 에 같은 줄을
적습니다. `scripts/sync_pdf_library.py` 는 `_구버전` 으로 시작하는 폴더를 건너뛰어 구판이 사이트로 다시 올라오지 않습니다.

### 관리자 가림막

오른쪽 위 자물쇠 단추로 엽니다. 켜면 물질 탭이 나타나고, 관리자 패널에서
`review.html`(PDF 추출 후보 검토)과 `pdf-queue.html`(PDF 미등록 자료 검토)로도
갑니다. 이 둘은 전부터 있었지만 어디에도 링크가 없어 주소를 외워야 했습니다.

**이것은 잠금이 아니라 가림막입니다.** GitHub Pages 정적 사이트라 서버가 없고,
암호를 확인하는 코드가 `js/admin-gate.js` 안에 있으며, 저장소가 공개라 그 코드를
누구나 읽을 수 있습니다. 브라우저 저장값을 직접 바꾸는 것도 막지 못합니다.
암호를 그대로 적지 않고 SHA-256 해시만 둔 것은 어깨너머로 보이는 것을 줄일 뿐입니다.

목적은 지키는 것이 아니라 치우는 것입니다. 현장에서 QR 을 찍는 작업자에게 물질
대장이나 PDF 검토 화면은 쓸 일이 없고 탭에 있으면 헷갈리기만 합니다.
**그러니 이 뒤에는 감춰서 아쉬운 것만 둡니다. 새어 나가면 안 되는 것은 애초에
이 사이트에 올리지 않습니다.**

암호를 바꾸는 길은 둘입니다. 어느 쪽이든 `js/admin-gate.js` 의 `PASS_HASH` 한 줄만
바뀝니다.

**터미널** — 판 번호까지 알아서 올려 주므로 이쪽이 안전합니다.

```
py scripts/set_admin_passcode.py "새암호"
```

**화면** — 관리자 패널의 `암호 바꾸기` 단추. 새 암호를 넣으면 넣을 줄을 통째로
만들어 주고, 복사 단추와 GitHub 편집 화면 링크를 같이 내놓습니다. 붙여 넣고
`Commit changes` 만 누르면 됩니다.

단추가 파일을 직접 고치지는 못합니다. 서버가 없는 정적 사이트라 브라우저가 남의
서버에 있는 파일을 쓸 수 없습니다. 기계가 할 수 있는 일(해시 만들기, 줄 맞추기,
그 파일 찾아가기)만 맡고 마지막 붙여넣기는 사람이 합니다. 새 암호는 아무 데도
저장하지 않고 해시를 만드는 데만 씁니다.

`js/admin-gate.js` 는 서비스워커에서 네트워크 우선으로 받습니다. 암호를 바꾸는
것은 판 번호와 상관없는 일이라 캐시 우선으로 두면 한 번 들어온 브라우저에 옛
암호가 남습니다. 실제로 겪었던 일입니다.

암호 자체는 어디에도 저장하지 않습니다. 저장소에 남는 것은 SHA-256 값뿐입니다.
**암호를 주석이나 문자열로 적어 두면 안 됩니다.** 저장소가 공개라 적는 순간
가림막 구실조차 못 합니다. 한 번 저질렀던 실수라서
`tests/test_site_ui_contract.py` 가 파일 안의 낱말을 모두 해시해 보고 잡습니다.

이 뒤에 두는 것이 감춰서 아쉬운 정도라는 전제 때문에, 다른 곳에서 쓰는 암호는
절대 쓰지 않습니다.

관리자 화면을 하나 더 두려면 같은 파일의 `ADMIN_PAGES` 에 줄을 더하면 패널에
바로 나옵니다.

### 물질 화면

조회 화면이 제품에서 성분으로 내려간다면 물질 화면은 그 반대입니다. 작업환경측정
계획을 세우거나 특수건강진단 대상을 추릴 때 쓰라고 만들었습니다.

묶는 기준은 CAS 번호 하나뿐입니다. 이름으로는 묶지 않습니다. 업체마다 자일렌을
자일렌·크실렌·Xylene·자일롤 로 달리 적어서, 이름으로 묶으면 같은 물질이 넷으로
갈라집니다. 반대로 CAS 가 없거나 영업비밀인 성분은 아예 묶지 않고 따로 둡니다.
억지로 묶으면 엉뚱한 성분끼리 한 덩어리가 됩니다.

법정분류 배지는 원본 MSDS 제3항 표에 적힌 것을 그대로 옮긴 것입니다. 사이트가
판정하는 것이 아니라서 문구도 "대상"이 아니라 "유해인자"로 적습니다. 원본이 비워
둔 칸은 "해당없음"이 아니라 "표기 없음"으로 둡니다. 화면에도 같은 뜻의 안내를
띄웁니다.

특별관리물질 배지는 넣지 않았습니다. 227건 가운데 16건만 원문에 표기가 있고 그
표기도 제각각이라("불용성화합물만 특별관리물질" 같은 조건부 주석), 배지를 달면
나머지 211건이 "표기 없음"이 아니라 "해당 아님"으로 읽힙니다.

## 실행 방법

현장용 로컬 실행은 `start_msds_site.bat` 파일을 더블클릭해서 사용합니다. `index.html` 파일을 직접 더블클릭하는 방식보다 로컬 서버 실행 방식이 JSON과 PDF를 안정적으로 불러옵니다.

```text
C:\Users\lsy16\Documents\GitHub\msds-site-prototype\start_msds_site.bat
```

기본 화면은 아래 순서로 데이터를 읽습니다.

- `data/msds.local.json`이 있으면 로컬 변환 데이터 모드로 표시됩니다.
- `data/msds.local.json`이 없고 `data/msds.public.json`이 있으면 공개 운영 데이터 모드로 표시됩니다.
- local/public 데이터가 없거나 읽기 실패하면 `data/msds-sample.json`을 읽습니다.
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

GitHub Pages 공개 운영을 위해 `pdf/` 폴더의 실제 MSDS PDF는 저장소에 올릴 수 있습니다. PDF 연결 검사는 로컬 PC의 `pdf/` 폴더 구조를 기준으로 수행합니다.

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

사이트는 제품 기본정보를 읽은 뒤 `data/msds-overrides.local.json`을 추가로 읽어 PDF 추출 후보 또는 검토완료 정보를 제품에 연결합니다. 로컬 override가 없으면 `data/msds-overrides.sample.json`을 사용하고, 둘 다 없거나 읽기 실패해도 기본 조회 화면은 계속 동작합니다.

PDF 추출 결과는 내부적으로 `reviewStatus`와 `extractStatus`를 가집니다. 현장용 화면에서는 `PDF 추출 후보`, `검토필요` 같은 문구를 숨기고 깔끔한 요약정보처럼 표시할 수 있습니다.

표시 모드는 `js/app.js`의 `APP_CONFIG`에서 관리합니다.

```text
fieldDisplayMode
showReviewStatusOnFieldPoster
showExtractionStatusInDetail
allowCandidateOverrideDisplay
```

운영 전에는 내부 검토를 거쳐 `reviewStatus`를 `검토완료`로 바꾸는 것을 권장합니다. 현장용 화면은 깔끔한 요약정보 표시를 우선하지만, 정식 근거자료는 항상 PDF 원본입니다.

최종 구축 방향은 엑셀을 제품 검색용 보조 색인으로 사용하고, PDF 원본에서 제품정보와 안전문구를 자동 또는 반자동으로 구축한 뒤 사람이 검토완료 처리하는 구조입니다.

## PDF 추출 후보 내부 검토

내부 검토자는 아래 화면에서 PDF 추출 후보를 확인할 수 있습니다.

```text
review.html
```

`index.html`은 현장 작업자용 조회 화면이고, `review.html`은 내부 검토자가 `data/msds-overrides.local.json`의 추출 후보를 확인하고 `reviewStatus`를 관리하는 화면입니다.

검토 화면에서는 아래 상태를 선택할 수 있습니다.

- 검토필요
- 검토완료
- 수정필요
- 제외

추천 검토 흐름은 아래와 같습니다.

1. `review.html`에 접속합니다.
2. `검토필요` 항목을 선택합니다.
3. 원본 PDF 미리보기와 추출 후보를 비교합니다.
4. `검토완료`, `수정필요`, `제외` 중 하나를 선택합니다.
5. 필요하면 `다음 검토필요 항목` 버튼으로 다음 항목으로 이동합니다.
6. 모든 변경 후 `수정 JSON 다운로드`를 실행합니다.
7. `apply_reviewed_overrides.py --dry-run`으로 다운로드 파일을 검증합니다.
8. 문제가 없으면 실제 적용합니다.
9. `audit_msds_workflow.py`를 다시 실행해 `검토필요` 수가 줄었는지 확인합니다.

PDF 2번 항목에서 신호어, 그림문자, 유해위험문구가 `해당없음` 또는 `분류되지 않음` 계열인데 GHS 후보가 추출된 경우, 검토 화면에 충돌 안내가 표시될 수 있습니다. 이 경우 원본 PDF의 표지요소를 확인하고, 현장용 화면에서는 모순된 GHS 그림문자가 표시되지 않도록 처리합니다.

정적 웹사이트는 로컬 JSON 파일을 직접 덮어쓸 수 없으므로, 검토 화면에서 상태를 바꾼 뒤 `msds-overrides.reviewed.local.json` 파일을 다운로드합니다. 다운로드한 파일을 사람이 확인한 다음 `data/msds-overrides.local.json`으로 교체해서 사용합니다.

`data/msds-overrides.local.json`은 실제 제품정보와 PDF 후보 정보가 들어갈 수 있는 로컬 전용 파일이므로 GitHub에 올리지 않습니다. 운영 전 최종 확인 대상은 `reviewStatus`가 `검토완료`인 항목을 기준으로 삼는 것을 권장합니다.

다운로드한 검토 결과를 적용할 때는 보조 스크립트를 사용할 수 있습니다. 먼저 dry-run으로 JSON 구조와 상태별 건수를 확인합니다.

```bash
python scripts/apply_reviewed_overrides.py --input msds-overrides.reviewed.local.json --dry-run
```

문제가 없으면 아래처럼 적용합니다.

```bash
python scripts/apply_reviewed_overrides.py --input msds-overrides.reviewed.local.json
```

적용 시 기존 `data/msds-overrides.local.json`이 있으면 `data/backups/msds-overrides.local.YYYYMMDD_HHMMSS.json` 형태로 자동 백업한 뒤 새 파일을 적용합니다. `data/msds-overrides.local.json`, `data/backups/`, `*reviewed.local.json` 파일은 실제 검토 데이터가 들어갈 수 있으므로 GitHub에 올리지 않습니다.

전체 PDF를 투입하기 전에는 운영 상태 점검 리포트를 먼저 확인하는 것을 권장합니다.

```bash
python scripts/audit_msds_workflow.py
```

이 스크립트는 엑셀 변환 제품 수, 성분정보 수, PDF 연결 상태, override 추출 상태, `reviewStatus`별 건수, PDF는 있으나 override가 없는 항목, override는 있으나 PDF가 없는 항목을 요약합니다.

리포트는 아래 로컬 파일로 생성됩니다.

```text
reports/msds-workflow-audit.local.json
reports/msds-workflow-audit.local.csv
```

local report에는 실제 제품/PDF 정보가 들어갈 수 있으므로 GitHub에 올리지 않습니다. 전체 PDF 투입 전 이 리포트로 PDF 연결, override 생성 여부, 검토완료 상태를 확인합니다.

## 작업자 주의 포인트

오른쪽 상세정보의 `작업자 주의 포인트`는 제품명, 유해성 문구, 위험물 구분, 성분정보, 보호구 문구를 바탕으로 로컬 규칙에 따라 표시합니다. 화면에서는 현장 작업, 보호구, 환기 및 노출관리, 화재·보관, 법적관리 확인사항처럼 필요한 파트만 나누어 보여줍니다.

- 외부 AI API나 OpenAI API를 호출하지 않습니다.
- API 토큰을 사용하지 않습니다.
- 현장 화면에서는 `검토필요`, `추출 후보` 같은 내부 검토 문구를 숨깁니다.
- 작업자 주의 포인트는 법적 MSDS를 대체하지 않는 참고용 안내입니다.
- 정식 근거자료는 항상 원본 PDF와 정식 MSDS입니다.

## 주의사항

- 실제 회사 엑셀 원본은 이 저장소에 넣지 않습니다.
- GitHub Pages 공개 운영에 필요한 MSDS PDF는 `pdf/` 폴더에 넣어 저장소에 올릴 수 있습니다.
- 실제 내부자료, 거래처 자료, 운영 데이터는 GitHub에 올리지 않습니다.
- 실제 엑셀 원본은 로컬 PC의 `data/raw/`에만 둡니다.
- 변환 결과인 `data/msds.local.json`도 GitHub에 올리지 않습니다.
- PDF 요약 후보 파일인 `data/msds-overrides.local.json`도 GitHub에 올리지 않습니다.
- 공개용 변환 결과인 `data/msds.public.json`, `data/msds-overrides.public.json`은 GitHub Pages용으로 커밋할 수 있습니다.

실제 PDF를 연결할 때는 `pdf/` 폴더의 기존 하위폴더 구조를 유지하고, public JSON의 `pdfPath` 또는 `relativePath`와 맞춰 관리합니다.

현재 `.gitignore` 설정으로 엑셀 파일, `data/raw/`, `data/original/`, `data/msds.local.json`, `data/*.local.json`, reports local 파일은 GitHub에 올라가지 않도록 제외되어 있습니다. 단, `pdf/` 폴더 안의 PDF는 GitHub Pages 공개 운영을 위해 추적할 수 있습니다.

## 디자인 수정 위치

화면 디자인은 주로 아래 파일에서 수정합니다.

```text
css/style.css
```

CSS 상단의 변수 영역에서 색상, 테두리, 여백, 글자 크기를 조정할 수 있습니다.

좌측 현장 요약판, 검색 영역, 우측 상세패널은 CSS 주석으로 구분되어 있어 나중에 `A4 안내문 스타일`, `카드형 스타일`, `모바일 간편조회 스타일`로 바꾸기 쉽게 정리되어 있습니다.

## 비MSDS 제외 항목 audit 기준

QR코드/안내문/카탈로그 등 실제 MSDS가 아닌 PDF는 `pdf-queue.html`에서 제외 처리합니다. 제외 처리된 비MSDS PDF는 audit에서 일반 PDF 추출 실패가 아니라 비MSDS 제외 항목으로 분리되어 집계됩니다.

이 처리는 실제 PDF 파일을 삭제하거나 이동하지 않고, 로컬 큐의 `reviewDecision`과 `excludeReason` 상태값으로만 관리합니다.

이미 PDF 추출 실패 상태의 override가 있더라도, 같은 PDF가 큐에서 `제외` 및 `QR코드/안내문`, `비MSDS`, `카탈로그/기타자료` 계열 사유로 분류되어 있으면 일반 추출 실패 수에서 제외하고 별도 제외 수로 집계합니다.
## PDF 라이브러리 인벤토리

전체 PDF를 투입하기 전에는 `pdf/` 폴더를 하위폴더까지 재귀적으로 스캔해 PDF 인벤토리를 먼저 생성합니다.

```bash
python scripts/build_pdf_inventory.py
```

이 스크립트는 PDF 파일을 수정, 삭제, 이동, 이름변경하지 않고 읽기 전용으로 확인합니다. 각 PDF의 상대경로, 파일명, 파일크기, 수정일, SHA-256 해시, 텍스트 추출 상태, 제품명 후보, CAS No. 후보, MSDS번호 후보, 텍스트 fingerprint를 기록합니다.

생성되는 로컬 전용 파일은 아래와 같습니다.

```text
data/pdf-inventory.local.json
reports/pdf-inventory-report.local.json
reports/pdf-inventory-report.local.csv
```

이 local report와 local inventory 파일들은 실제 PDF 목록과 제품 후보 정보가 들어갈 수 있으므로 GitHub에 올리지 않습니다. 저장소에는 구조 참고용 `data/pdf-inventory.sample.json`과 공개 운영용 public JSON만 올립니다.

인벤토리에서는 아래 항목을 확인합니다.

- 같은 SHA-256 해시를 가진 완전 중복 PDF: `exact_duplicate_pdf`
- 같은 파일명이 여러 하위폴더에 있는 경우: `filename_duplicate`
- 파일명은 다르지만 내부 텍스트 fingerprint 또는 CAS 후보가 유사한 경우: `possible_content_duplicate`
- 엑셀 제품 하나에 여러 PDF 후보가 연결될 수 있는 경우: `multiple_pdf_candidates`
- PDF는 있지만 엑셀 변환 데이터에 없는 경우: `excel_missing_pdf`

내용 유사 후보는 자동 삭제, 이동, 이름변경하지 않고 리포트에 확인 필요 대상으로 남깁니다. SHA-256이 같은 완전 중복은 사용자 승인, 대표본 선정, 백업을 거친 경우에만 `deduplicate_pdf_library.py --apply`로 정리할 수 있습니다.

PDF 미리보기는 앞으로 `fileName`뿐 아니라 `relativePath` 또는 `pdfPath`도 사용할 수 있습니다.

```json
{
  "fileName": "PN3021.pdf",
  "relativePath": "3M/PN3021.pdf",
  "pdfPath": "/pdf/3M/PN3021.pdf"
}
```

현재처럼 `pdf/` 바로 아래에 있는 파일도 계속 지원합니다.

## 엑셀 갱신 후 재점검 흐름

엑셀이 수정되면 아래 순서로 다시 점검합니다.

1. `data/raw/`에 최신 엑셀을 저장합니다.
2. `convert_excel_to_json.py`를 실행해 `data/msds.local.json`을 갱신합니다.
3. `build_pdf_inventory.py`를 실행해 PDF 인벤토리를 갱신합니다.
4. `check_pdf_links.py` 또는 `audit_msds_workflow.py`를 실행합니다.
5. PDF 연결, PDF 미등록, 엑셀 미등록 PDF, 중복 의심, 매핑 필요 항목을 확인합니다.

전체 PDF를 투입할 때는 먼저 현재 테스트 PDF 상태를 Commit/Push한 뒤, 실제 PDF 원본 폴더 구조를 `pdf/` 아래에 그대로 복사합니다. 그 다음 GitHub Desktop에 PDF 파일이 변경 목록으로 뜨지 않는지 확인하고, 인벤토리와 audit 리포트를 실행해 상태를 점검합니다. 일부 항목을 `review.html`에서 검토한 뒤 문제가 없으면 전체 PDF 요약 추출을 진행합니다.

## PDF 매칭 점수 기준

PDF와 엑셀 제품의 연결 후보는 단순히 CAS No.가 하나 겹치는지만 보지 않고, 파일명, 수동 매핑, 제품명, ERP명, MSDS번호, CAS No., 공급업체명, 파일명 키워드를 종합해 점수로 분류합니다.

- `strong_match_candidate`: 90점 이상
- `probable_match_candidate`: 60점 이상 90점 미만
- `weak_match_candidate`: 30점 이상 60점 미만
- `low_confidence`: 30점 미만으로 기본 후보에서 제외

파일명 정확 일치와 수동 매핑은 가장 강한 근거로 봅니다. CAS No.가 2개 이상 겹치면 약한 후보 근거가 될 수 있지만, CAS No. 1개만 겹치는 경우는 흔한 성분 때문에 오탐 가능성이 있어 낮은 점수로만 기록하고 단독 후보로 확정하지 않습니다.

한 제품에 여러 PDF 후보가 있을 때도 `strong` 또는 `probable` 후보가 2개 이상일 때만 `multiple_pdf_candidates`로 집계합니다. 이미 파일명 정확 일치가 있는 제품은 약한 내용 기반 후보를 여러 후보 집계에서 제외합니다.

내용 유사 후보는 자동 삭제, 이동, 이름변경하지 않고 확인 필요 리포트로 관리합니다. 완전 중복만 별도 백업 후 대표본 하나로 정리할 수 있습니다.

## PDF 라이브러리 동기화

회사 원본 MSDS 폴더를 사이트용 `pdf/` 폴더에 다시 반영할 때는 바로 덮어쓰기하지 않고, 먼저 dry-run으로 변경점을 확인합니다.

```bash
python scripts/sync_pdf_library.py --source "D:\MSDS 원본" --target pdf --dry-run
```

문제가 없을 때만 아래처럼 실제 적용합니다.

```bash
python scripts/sync_pdf_library.py --source "D:\MSDS 원본" --target pdf --apply
```

기본 원칙은 다음과 같습니다.

- `--dry-run` 또는 옵션 없음: 파일을 바꾸지 않고 변경점 리포트만 생성
- `--apply`: 신규 PDF와 같은 경로에서 내용이 바뀐 PDF만 복사
- 같은 경로의 기존 PDF를 덮어쓸 때는 `data/backups/pdf-sync/` 아래에 먼저 백업
- 원본에서 사라진 PDF는 `deleted_from_source`로 리포트만 남기고 자동 삭제하지 않음
- 파일 이동/이름변경 의심, 완전 중복, 같은 파일명 중복은 확인 필요 대상으로만 표시

동기화 리포트는 로컬 전용 파일로 생성됩니다.

```text
reports/pdf-sync-preview.local.json
reports/pdf-sync-preview.local.csv
reports/pdf-sync-apply.local.json
reports/pdf-sync-apply.local.csv
```

동기화 후에는 아래 순서로 상태를 다시 확인합니다.

```bash
python scripts/build_pdf_inventory.py
python scripts/check_pdf_links.py --data data/msds.local.json --pdf-dir pdf
python scripts/audit_msds_workflow.py
```

필요하면 `sync_pdf_library.py`에 `--run-audit` 옵션을 붙여 후속 점검 스크립트를 함께 실행할 수 있습니다.

PDF 원본 폴더를 통째로 갱신할 때 권장 흐름은 아래와 같습니다.

1. 원본 MSDS 폴더를 정리합니다.
2. `sync_pdf_library.py --dry-run`을 실행합니다.
3. 신규, 변경, 중복, 삭제 의심 항목을 확인합니다.
4. 문제가 없으면 `sync_pdf_library.py --apply`를 실행합니다.
5. `build_pdf_inventory.py`를 실행합니다.
6. `check_pdf_links.py`를 실행합니다.
7. `audit_msds_workflow.py`를 실행합니다.
8. `review.html`에서 확인 필요한 항목을 검토합니다.

엑셀이 갱신된 경우에는 아래 순서로 다시 점검합니다.

1. 최신 엑셀을 `data/raw/`에 저장합니다.
2. `convert_excel_to_json.py`를 실행합니다.
3. `data/msds.local.json`이 갱신됩니다.
4. `build_pdf_inventory.py`를 실행합니다.
5. `check_pdf_links.py`를 실행합니다.
6. `audit_msds_workflow.py`를 실행합니다.

엑셀 원본과 `data/msds.local.json`은 실제 제품정보가 들어가므로 GitHub에 올리지 않습니다. 엑셀이 바뀌면 기존 PDF 매칭 상태도 반드시 audit로 다시 확인합니다.

## 엑셀 미등록 PDF 검토 큐

PDF 원본 라이브러리가 실제 기준이고, 엑셀은 아직 미완성 색인일 수 있습니다. 따라서 PDF는 있지만 엑셀에 없는 파일은 오류가 아니라 `엑셀 미등록 PDF`로 따로 관리합니다.

인벤토리를 만든 뒤 아래 스크립트를 실행합니다.

```bash
python scripts/build_pdf_registration_queue.py
```

이 스크립트는 `data/pdf-inventory.local.json`에서 `excel_missing_pdf` 상태의 PDF를 찾아 아래 로컬 전용 큐를 생성합니다.

```text
data/pdf-registration-queue.local.json
```

큐 항목은 `reviewDecision`으로 관리합니다.

- `미검토`
- `엑셀등록필요`
- `기존제품매핑필요`
- `중복의심`
- `제외`
- `보류`

기존 큐가 있으면 `reviewDecision`, 메모, 수동 입력 필드는 보존합니다. PDF 라이브러리에서 더 이상 보이지 않는 항목은 삭제하지 않고 `missing_from_pdf_library` 상태로 남겨 다시 확인할 수 있게 합니다.

PDF가 엑셀보다 많을 때 권장 흐름은 아래와 같습니다.

1. 원본 PDF 폴더를 `sync_pdf_library.py`로 반영합니다.
2. `build_pdf_inventory.py`를 실행합니다.
3. `build_pdf_registration_queue.py`를 실행합니다.
4. `audit_msds_workflow.py`를 실행합니다.
5. `data/pdf-registration-queue.local.json`에서 엑셀 미등록 PDF를 검토합니다.
6. 엑셀에 추가할 항목은 다음 엑셀 업데이트 때 반영합니다.
7. 엑셀 수정 후 `convert_excel_to_json.py`를 다시 실행합니다.
8. inventory와 audit을 다시 실행합니다.

`data/pdf-registration-queue.local.json`은 실제 PDF 목록과 검토 메모가 들어갈 수 있으므로 GitHub에 올리지 않습니다. 저장소에는 구조 참고용 `data/pdf-registration-queue.sample.json`만 올립니다.

엑셀 미등록 PDF는 아래 내부 화면에서 검토할 수 있습니다.

```text
pdf-queue.html
```

`pdf-queue.html`은 `data/pdf-registration-queue.local.json`을 읽어 미검토, 엑셀등록필요, 기존제품매핑필요, 중복의심, 제외, 보류 상태로 분류하는 내부 검토 화면입니다. local 큐가 없으면 `data/pdf-registration-queue.sample.json`을 사용하고, 둘 다 없으면 안내문을 표시합니다.

정적 웹사이트에서는 local JSON을 직접 덮어쓸 수 없으므로, 검토 화면에서 수정한 결과는 아래 파일명으로 다운로드됩니다.

```text
pdf-registration-queue.reviewed.local.json
```

다운로드한 큐 파일은 아래 보조 스크립트로 검증한 뒤 `data/pdf-registration-queue.local.json`에 반영합니다. 이 검토 화면과 적용 스크립트는 PDF 파일을 삭제, 이동, 이름변경하지 않고 상태와 메모만 분류합니다.

```bash
python scripts/apply_pdf_registration_queue.py --input "C:\Users\lsy16\Downloads\pdf-registration-queue.reviewed.local.json" --dry-run
python scripts/apply_pdf_registration_queue.py --input "C:\Users\lsy16\Downloads\pdf-registration-queue.reviewed.local.json"
```

`--dry-run`은 입력 JSON이 열리는지, 배열 구조인지, `relativePath`, `fileName`, `reviewDecision`이 있는지, `reviewDecision` 값이 허용 상태인지 확인하고 상태별 수량만 보여줍니다. 실제 파일은 바꾸지 않습니다.

`--dry-run` 없이 실행하면 기존 `data/pdf-registration-queue.local.json`을 먼저 아래 폴더에 백업한 뒤 검증된 큐를 적용합니다.

```text
data/backups/
```

`data/pdf-registration-queue.local.json`, `data/backups/`, `pdf-registration-queue.reviewed.local.json`은 실제 PDF 목록과 검토 메모가 들어갈 수 있으므로 GitHub에 올리지 않습니다.

권장 적용 흐름은 아래와 같습니다.

1. `pdf-queue.html`에 접속합니다.
2. 엑셀 미등록 PDF 상태를 분류합니다.
3. `수정 큐 JSON 다운로드`로 reviewed local 파일을 받습니다.
4. `apply_pdf_registration_queue.py --dry-run`으로 검증합니다.
5. 문제가 없으면 `apply_pdf_registration_queue.py`로 실제 적용합니다.
6. `audit_msds_workflow.py`를 다시 실행합니다.
7. 미검토, 엑셀등록필요, 중복의심, 제외, 보류 수량을 확인합니다.

## PDF-first 배치 추출 흐름

이 프로젝트에서는 엑셀을 최종 DB가 아니라 아직 미완성인 검색 색인으로 봅니다. 실제 관리 기준은 `pdf/` 폴더에 들어 있는 PDF 원본 전체이며, 엑셀에 아직 등록되지 않은 PDF도 요약 추출과 내부 검토 대상입니다.

전체 PDF를 한 번에 확정하지 말고, 아래처럼 일부씩 배치 추출하고 검토하는 방식을 권장합니다.

```bash
python scripts/extract_pdf_summary.py --pdf-dir pdf --output data/msds-overrides.local.json --only-missing-overrides --limit 20
python scripts/extract_pdf_summary.py --pdf-dir pdf --output data/msds-overrides.local.json --target excel-missing --limit 20
python scripts/extract_pdf_summary.py --pdf-dir pdf --output data/msds-overrides.local.json --target excel-linked --limit 20
```

추출된 override에는 PDF가 엑셀 등록 제품과 연결된 것인지, 엑셀 미등록 PDF인지 구분하기 위해 아래 정보가 함께 저장됩니다.

- `pdfRegistrationType`: `excel_linked` 또는 `excel_missing_pdf`
- `excelProductMatched`: 엑셀 제품과 연결되었는지 여부
- `sourceRelativePath`: `pdf/` 기준 상대경로
- `queueReviewDecision`: 엑셀 미등록 PDF 큐의 검토 결정값

기존 `data/msds-overrides.local.json`에 있는 항목은 fileName 또는 relativePath 기준으로 병합됩니다. `검토완료`, `수정필요`, `제외` 상태와 사람이 작성한 `manual*`, `reviewed*`, 메모 필드는 재추출로 초기화하지 않습니다.

배치 추출 후에는 아래 local report가 생성됩니다.

```text
reports/pdf-summary-batch-extract.local.json
reports/pdf-summary-batch-extract.local.csv
```

PDF-first 권장 운영 흐름은 아래와 같습니다.

1. `sync_pdf_library.py`로 PDF 원본 폴더를 반영합니다.
2. `build_pdf_inventory.py`를 실행합니다.
3. `build_pdf_registration_queue.py`를 실행합니다.
4. `extract_pdf_summary.py --only-missing-overrides --limit 20`으로 일부씩 추출합니다.
5. `review.html`과 `pdf-queue.html`에서 추출 후보와 엑셀 미등록 PDF를 검토합니다.
6. 검토 결과 JSON을 다운로드하고 apply 스크립트로 적용합니다.
7. `audit_msds_workflow.py`를 실행해 override, 검토상태, 엑셀 등록/미등록 PDF 수량을 확인합니다.

추출 결과는 자동 확정값이 아니며, 기본 `reviewStatus`는 `검토필요`입니다. 운영 전 내부 검토를 거쳐 필요한 항목을 `검토완료`로 바꾸는 것을 권장합니다.

배치 추출 전에 현재 Python 환경에 필요한 패키지가 설치되어 있는지 확인합니다.

```bash
python -m pip install -r requirements.txt
```

특히 `pypdf`가 없는 Python으로 실행하면 PDF 텍스트 추출이 전부 실패처럼 보일 수 있습니다. 최신 스크립트는 `pypdf`가 없으면 override를 만들지 않고 중단하도록 처리합니다.

이미 `data/msds-overrides.local.json`에 실패 상태로 들어간 항목은 아래 옵션으로 다시 추출할 수 있습니다.

```bash
python scripts/extract_pdf_summary.py --pdf-dir pdf --output data/msds-overrides.local.json --retry-failed --limit 20
```

`--retry-failed`는 기존 override 중 `text_extract_failed`, `scanned_pdf_or_image_pdf`, `manual_review_required`, `pypdf_import_failed` 또는 error/notes에 `pypdf_import_failed`가 있는 항목만 다시 처리합니다. 재추출해도 기존 `reviewStatus`, `검토완료`, `수정필요`, `제외`, `manual*`, `reviewed*`, 사람이 작성한 notes는 보존됩니다.

## 비MSDS PDF 제외 흐름

`pdf/` 폴더에는 실제 MSDS 원본 외에도 QR코드 안내문, 표지, 카탈로그, 브로슈어, 시험성적서, 인증서, 사진 파일을 PDF로 만든 자료가 섞일 수 있습니다. 이런 파일은 PDF 파일이더라도 엑셀등록필요 대상으로 바로 보지 않고, `pdf-queue.html`에서 제외 또는 보류로 분류합니다.

큐 생성 시 파일명이나 상대경로에 아래 키워드가 있으면 자동 확정하지 않고 `비MSDS확인필요`로 표시합니다.

```text
QR, QR코드, 코드, 안내, 표지, 카탈로그, catalog, brochure, 시험성적, 성적서, 인증서, 사진, 이미지
```

`pdf-queue.html` 상세 화면에는 빠른 제외 버튼이 있습니다.

- `비MSDS 제외`
- `QR코드/안내문 제외`
- `카탈로그/기타 제외`

버튼을 누르면 `reviewDecision`은 `제외`가 되고, `excludeReason`에는 각각 `비MSDS`, `QR코드/안내문`, `카탈로그/기타자료`가 자동 입력됩니다. 이 처리는 local queue에 상태만 기록하며 PDF 파일을 삭제, 이동, 이름변경하지 않습니다.

`extract_pdf_summary.py`는 기본적으로 `reviewDecision`이 `제외`이고 `excludeReason`이 비MSDS, QR코드/안내문, 카탈로그 계열인 항목을 요약 추출 대상에서 제외합니다. 필요할 때만 `--no-skip-excluded` 옵션으로 포함할 수 있습니다.

`audit_msds_workflow.py`에서는 엑셀 미등록 PDF 중 제외 수, 비MSDS 제외 수, QR코드/안내문 제외 수, 카탈로그/기타 제외 수, 비MSDS 의심표시 수, 순수 미검토 등록 대상 수를 확인할 수 있습니다. 이미 override에 실패 기록이 있더라도 큐에서 비MSDS/QR코드/안내문으로 제외된 PDF는 PDF 추출 실패가 아니라 비MSDS 제외 항목으로 별도 집계합니다.

즉 QR코드 안내문이나 카탈로그는 PDF 파일을 삭제하지 않고, local queue의 상태만 `제외`와 `excludeReason`으로 기록합니다. 이후 기본 배치 추출과 `--retry-failed`에서도 제외되며, audit에서는 추출 실패 수와 분리되어 표시됩니다.

## 긴 텍스트와 반응형 화면

현장 조회 화면과 내부 검토 화면은 긴 제품명, PDF 파일명, 하위폴더 상대경로, 성분명, CAS 정보가 화면 폭을 밀어내지 않도록 줄바꿈 기준을 공통으로 적용합니다.

- `index.html`, `review.html`, `pdf-queue.html`은 좁은 화면에서 1열 흐름을 우선합니다.
- 긴 파일명과 상대경로는 목록 안에서 2~3줄까지만 보이고, 상세 영역에서는 칸 안에서 자연스럽게 줄바꿈됩니다.
- 성분정보 표는 작은 화면에서 표 전체가 화면을 깨뜨리지 않도록 표 영역 안에서 가로 스크롤로 확인합니다.
- PDF 미리보기는 `PDF 미리보기` 버튼을 눌렀을 때 같은 영역 안에 표시하며, 좁은 화면에서는 PDF 영역이 아래로 이어지도록 배치합니다.

디자인이나 줄바꿈 기준을 바꾸려면 `css/style.css`의 `Long text and responsive stability`, `Ingredient section`, `PDF registration queue review page`, `Mobile stacked flow` 영역을 우선 확인하면 됩니다.
## GHS code-based display and extraction

The field page now renders GHS pictograms from `ghsCodes` first, while keeping legacy `ghsPictograms` for compatibility.

- `GHS01`: 폭발성
- `GHS02`: 인화성
- `GHS03`: 산화성
- `GHS04`: 고압가스
- `GHS05`: 부식성
- `GHS06`: 급성독성
- `GHS07`: 유해/자극성
- `GHS08`: 건강유해성
- `GHS09`: 환경유해성

GHS SVG assets live in `assets/ghs/ghs01.svg` through `assets/ghs/ghs09.svg`. These are local GHS-style display assets, not externally downloaded official files.

PDF extraction assigns GHS codes only from MSDS section 2 hazard classification / pictogram / signal word / hazard statement evidence. Words found only in precaution, storage, disposal, fire response, or PPE sections must not create extra pictograms.

H-code statements are kept in the hazard statement area, P-code statements are kept in the precautionary statement area, and PPE candidates are limited to real PPE or exposure-control sentences such as gloves, goggles, respirators, ventilation, and local exhaust.

# MSDS 로컬 운영 안내

로컬 운영 방식과 회사 노트북에서 새 PDF를 추가하는 절차는 OneDrive 운영문서 폴더의 `로컬 운영 및 PDF 추가 가이드`를 기준으로 합니다.

현장용 로컬 실행 방법은 OneDrive 운영문서 폴더의 `현장용 로컬 실행 가이드`를 확인하세요. 비개발자는 프로젝트 폴더의 `start_msds_site.bat` 파일을 더블클릭해 현장 검색용 화면을 실행하면 됩니다.

GitHub Pages 인터넷 배포는 OneDrive 운영문서 폴더의 `GitHub Pages 인터넷 배포 가이드`를 기준으로 합니다. 공개 URL은 <https://lsy1659-ux.github.io/msds-site-prototype/> 입니다. GitHub Pages 실제 MSDS PDF 미리보기 공개 운영은 완료되었고, 공개 사이트는 `data/msds.public.json`, `data/msds-overrides.public.json`, `pdf/` 폴더의 대표 PDF 224개를 사용합니다. 실제 엑셀, raw 데이터, original 데이터, `.env`, local JSON, reports local 파일은 GitHub에 올리지 않습니다. 실제 현장 사용은 여전히 `start_msds_site.bat` 로컬 실행을 기준으로 할 수 있습니다.

모바일 브라우저에서 PDF가 자동 다운로드되는 것을 막기 위해 PDF 원본은 페이지 로드나 제품 선택 직후 자동 삽입하지 않습니다. 사용자가 `PDF 미리보기` 버튼을 누른 경우에만 PDF.js로 사이트 안에 미리보기를 표시합니다. 현재 최소 수정안은 CDN PDF.js를 사용하므로 인터넷 연결이 필요합니다. 더 안정적인 운영이 필요하면 `vendor/pdfjs/` 또는 `lib/pdfjs/`에 PDF.js 정적 파일을 포함하고 `js/app.js`의 PDF.js 경로를 내부 경로로 바꿉니다.

PDF.js 미리보기는 전체 페이지를 세로로 렌더링해 사이트 안에서 스크롤로 확인하는 방식입니다. 확대, 축소, 폭맞춤을 사용할 수 있습니다. PDF는 GitHub Pages에 공개되어 있으므로 주소를 직접 알면 기술적으로 다운로드를 완전히 막을 수는 없지만, 사이트 UI에서는 다운로드나 새 탭 열기를 제공하지 않고 내부 미리보기를 기본 흐름으로 사용합니다.

공개용 데이터 생성:

```powershell
python scripts/build_public_data.py
```

실행 전 로컬 환경 점검:

```powershell
python scripts/check_local_runtime_ready.py
```

incoming PDF 점검:

```powershell
python scripts/check_incoming_pdfs.py
```
