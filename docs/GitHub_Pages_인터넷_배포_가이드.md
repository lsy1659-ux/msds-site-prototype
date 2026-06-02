# GitHub Pages 인터넷 배포 가이드

## 배포 목적

GitHub Pages 배포는 MSDS 조회 사이트의 공개용 정적 화면을 인터넷에서 확인하기 위한 용도입니다. 현재 공개 배포 화면은 `data/msds.public.json`, `data/msds-overrides.public.json`, `pdf/` 폴더의 PDF를 사용해 실제 제품 검색과 PDF 미리보기를 제공합니다.

## 배포 완료 기록

- 완료 상태: GitHub Pages 실제 MSDS PDF 미리보기 공개 운영 완료
- 최초 배포 완료일: 2026-06-02
- 실제 PDF 공개 운영 최종 확인일: 2026-06-03
- 공개 URL: <https://lsy1659-ux.github.io/msds-site-prototype/>

공개 사이트는 공개용 MSDS 데이터와 `pdf/` 폴더의 PDF 239개를 사용합니다. 로컬 실행은 `start_msds_site.bat`로 실행하며, local JSON이 있으면 local 데이터를 우선 사용합니다.

## 배포 후 확인 완료 항목

- 사이트 접속 정상
- 실제 제품 검색 정상
- 제품 상세정보 표시 정상
- `data/msds.public.json` 접근 정상
- `data/msds-overrides.public.json` 접근 정상
- 공개 운영 안내 문구 표시 정상
- 실제 PDF 미리보기/새 탭 열기 정상
- `pdf/` 폴더의 PDF 239개 공개 접근 가능
- `data/msds.local.json` 404/Not Found 정상
- `data/msds-overrides.local.json` 404/Not Found 정상
- `reports/*.local.*` 404/Not Found 정상
- 실제 엑셀, `data/raw/`, `data/original/`, `.env` 비공개 유지

## 공개 배포 시 주의사항

GitHub Pages 공개 운영을 위해 `pdf/` 폴더의 PDF와 public JSON은 GitHub에 올릴 수 있습니다. 단, 실제 엑셀, raw 데이터, 실사용 local JSON, local report는 올리지 않습니다.

아래 항목은 공개 저장소와 GitHub Pages에 노출되면 안 됩니다.

- 실제 엑셀 파일
- `data/raw/`
- `data/original/`
- `data/msds.local.json`
- `data/msds-overrides.local.json`
- `reports/*.local.*`
- 회사 내부자료 또는 현장 운영 전용 자료

아래 항목은 공개 배포 대상으로 사용할 수 있습니다.

- `data/msds.public.json`
- `data/msds-overrides.public.json`
- `pdf/` 폴더의 MSDS PDF

public JSON은 local JSON을 직접 커밋하지 않고 아래 명령으로 생성합니다.

```powershell
python scripts/build_public_data.py
```

## 모바일 PDF 미리보기 기준

모바일 브라우저에서는 PDF 원본을 iframe, object, embed에 바로 넣으면 브라우저가 미리보기 대신 자동 다운로드로 처리할 수 있습니다. 그래서 공개 화면은 사이트 접속 직후나 제품 선택 직후 PDF를 자동 로드하지 않습니다.

PDF 영역에는 먼저 파일 경로와 버튼만 표시합니다. 사용자가 `PDF 미리보기` 버튼을 누른 경우에만 PDF.js로 사이트 안에 PDF 뷰어를 표시합니다. 뷰어 안에서 이전/다음 페이지 이동, 현재 페이지 표시, 확대, 축소, 폭맞춤을 사용할 수 있습니다. `새 탭에서 열기`는 유지하지만 사용자가 직접 누를 때만 동작하는 보조 기능입니다.

현재 적용한 최소 수정안은 CDN PDF.js를 사용합니다. 이 방식은 빠르게 적용할 수 있지만, PDF 미리보기를 보려면 인터넷에서 CDN 파일을 불러올 수 있어야 합니다.

더 안정적인 수정안은 PDF.js 정적 파일을 `vendor/pdfjs/` 또는 `lib/pdfjs/` 폴더에 포함한 뒤, `js/app.js`의 PDF.js 경로를 내부 파일로 바꾸는 방식입니다. 이 경우 CDN 연결 상태와 무관하게 GitHub Pages와 로컬 실행에서 같은 PDF.js 파일을 사용할 수 있습니다.

## GitHub Pages 설정 방법

1. GitHub 저장소에 접속합니다.
2. `Settings`를 클릭합니다.
3. 왼쪽 메뉴에서 `Pages`를 클릭합니다.
4. `Build and deployment`에서 `Source`를 `Deploy from a branch`로 선택합니다.
5. `Branch`를 `main`, `Folder`를 `/root`로 선택합니다.
6. `Save`를 클릭합니다.
7. 생성된 사이트 주소를 확인합니다.

일반적인 주소 형식은 아래와 같습니다.

```text
https://사용자명.github.io/저장소명/
```

## 배포 후 확인할 것

배포 후 공개 사이트에서 아래 항목을 확인합니다.

- `index.html`이 열리는지
- CSS와 JavaScript가 정상 로드되는지
- local JSON이 없는 GitHub Pages에서 public JSON이 로드되는지
- "GitHub Pages 공개 운영 화면입니다. 공개용 MSDS 데이터와 PDF를 사용 중입니다." 안내가 표시되는지
- 제품 검색과 상세정보 표시가 정상인지
- PDF 미리보기와 새 탭 열기가 정상인지
- 실제 엑셀, local JSON, local report가 공개 사이트에서 접근되지 않는지

## 실제 운영 기준

현장 사용은 GitHub Pages 공개 운영 화면 또는 로컬 실행 화면을 사용할 수 있습니다. 집 PC에서는 로컬 실행 화면을 기준으로 개발, 데이터 생성, 검토를 진행합니다.

현장 검색용 화면은 프로젝트 폴더의 `start_msds_site.bat` 파일을 더블클릭해서 실행합니다. 이 방식은 로컬의 `data/msds.local.json`, `data/msds-overrides.local.json`, 실제 `pdf` 폴더를 사용합니다.

검토 및 관리용 화면은 `start_msds_review.bat` 파일을 더블클릭해서 실행합니다.

GitHub Pages는 공개용 public JSON과 `pdf/` 폴더의 PDF를 사용합니다. 로컬 실행은 local JSON을 우선 사용하고, GitHub Pages는 public JSON을 사용하며, sample 데이터는 public/local 데이터가 없을 때의 fallback 용도입니다.
