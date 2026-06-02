# 로컬 운영 및 PDF 추가 가이드

## 운영 원칙

이 저장소는 MSDS 사이트의 코드와 운영 문서를 GitHub로 동기화하기 위한 저장소입니다. 실제 MSDS PDF, 엑셀, 실사용 local JSON, local report는 각 PC의 로컬 환경에 보관하고 GitHub에는 올리지 않습니다.

집 PC는 메인 개발 및 총괄 관리 환경으로 사용합니다. 코드 개발, PDF 전체 투입, 추출, 검토, 보정, audit 작업은 집 PC에서 수행하는 것을 기준으로 합니다.

회사 노트북은 현장 사용 환경으로 사용합니다. 같은 GitHub 저장소를 받아 현장용 화면을 실행하고, 사용 중 새 MSDS PDF가 생기면 정식 PDF 폴더에 바로 섞지 않고 `incoming` 폴더에 먼저 넣어 점검합니다.

## GitHub에 올리는 것과 올리지 않는 것

GitHub에 올리는 대상은 코드, 샘플 데이터, 문서입니다.

GitHub에 올리지 않는 대상은 실제 PDF, 엑셀, 실사용 local JSON, local report입니다. 대표적으로 아래 파일과 폴더는 로컬 전용입니다.

- `*.pdf`
- `*.xlsx`
- `data/msds.local.json`
- `data/msds-overrides.local.json`
- `reports/*.local.*`
- `incoming/`
- `data/raw/`
- `data/original/`

실제 MSDS PDF가 공개 제공 자료 성격이라도, 용량, 운영 편의, PC별 경로 차이 때문에 GitHub 추적 대상에서 제외합니다.

## 화면 용도

`index.html`은 현장용 화면입니다. 사용자가 현장에서 MSDS를 찾고 확인하는 화면이므로, "검토필요", "추출후보" 같은 내부 검토 문구를 노출하지 않는 것을 기준으로 합니다.

`review.html`은 검토 및 관리용 화면입니다. 추출 결과 확인, 보정, 내부 검토 상태 확인 등 관리 목적의 화면으로 사용합니다.

## 집 PC 메인 관리 방식

1. GitHub 저장소를 최신 상태로 받습니다.
2. 실제 PDF는 로컬의 기존 PDF 폴더 구조에 보관합니다.
3. PDF 전체 투입, 추출, 검토, 보정, audit 작업을 수행합니다.
4. 실사용 데이터는 `data/msds.local.json`, 보정 데이터는 `data/msds-overrides.local.json`으로 관리합니다.
5. 코드, 샘플, 문서 변경만 GitHub에 반영합니다.
6. 실제 PDF, 엑셀, local JSON, local report가 GitHub Desktop 변경 목록에 올라오지 않는지 확인합니다.

## 회사 노트북 사용 방식

1. GitHub에서 같은 저장소를 받습니다.
2. 로컬에 필요한 실제 PDF와 local JSON을 준비합니다.
3. 실행 전 아래 명령으로 환경을 점검합니다.

```powershell
python scripts/check_local_runtime_ready.py
```

4. 현장 사용은 `index.html`을 기준으로 합니다.
5. 검토나 관리가 필요할 때만 `review.html`을 사용합니다.

## 회사에서 새 PDF 추가 절차

새 MSDS PDF는 정식 PDF 폴더에 바로 넣지 않습니다. 먼저 `incoming` 폴더에 넣고 중복 및 충돌 여부를 점검합니다.

1. 프로젝트 루트에 `incoming` 폴더가 없으면 로컬에서 만듭니다.
2. 새 PDF를 `incoming` 폴더에 넣습니다.
3. 아래 명령을 실행합니다.

```powershell
python scripts/check_incoming_pdfs.py
```

4. 결과 보고서를 확인합니다.

- `reports/incoming-pdf-check.local.csv`
- `reports/incoming-pdf-check.local.json`

5. "파일명 충돌", "동일 내용 중복 의심", "확인 필요" 항목은 자동 처리하지 않습니다.
6. 확인이 끝난 PDF만 기존 공정/업체별 PDF 폴더 구조에 맞춰 수동으로 반영합니다.

## 점검 기준

`check_local_runtime_ready.py`는 필수 코드 파일, 실사용 local 파일, PDF 폴더, `incoming` 폴더, `reports` 폴더, PDF 파일 수를 확인합니다. 누락된 항목은 "조치 필요"로 표시합니다.

`check_incoming_pdfs.py`는 `incoming` 폴더의 PDF를 기존 PDF 폴더와 비교합니다. 같은 파일명인데 내용이 다르면 "파일명 충돌"로 표시하고, 다른 파일명인데 내용이 같으면 "동일 내용 중복 의심"으로 표시합니다.

중복 의심 항목은 자동으로 이동, 삭제, 덮어쓰기, 이름변경하지 않습니다. 보고서에 "확인 필요"로 남기고 사람이 판단합니다.
