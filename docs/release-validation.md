# MSDS 공개 배포 검증

`scripts/validate_public_release.py`는 기본 실행 시 파일을 수정하지 않고 공개자료와 PDF 연결 상태를 검사한다. 오류가 하나라도 있으면 종료코드 1을 반환하므로 GitHub Pages 배포 전 안전장치로 사용할 수 있다.

## 검사 항목

- 공개 제품 223건과 실제 PDF의 일대일 연결
- 누락·중복 제품 ID와 중복 PDF 연결
- 최초 작성일과 최종 개정일의 순서 및 날짜 형식
- 제품 최종 개정일과 자동 추출 후보 개정일의 충돌
- 자동 추출정보 표시 설정과 PDF 원문 우선 안내 유지 여부
- PDF 경로 이탈, 누락 파일, 제품과 연결되지 않은 PDF
- 신호어 허용값: `위험`, `경고`, `해당없음`, 빈 값
- 잘못된 신호어·충돌 날짜가 공개 후보 필드에서 제거됐는지 여부
- 공개 JSON 및 PDF 묶음의 해시값을 기록한 릴리스 매니페스트

QR 안내 PDF인 `pdf/0. 캠스 MSDS QR 코드.pdf`만 제품 미연결 파일로 허용한다.
제품의 최초 작성일과 최종 개정일은 제품 식별·최신본 판단 정보로 항상 유지한다. 자동 추출 후보 날짜가 제품 날짜와 다르면 후보 날짜만 제외하고, 나머지 자동 추출 요약은 계속 표시한다.

## 직접 실행

저장소 최상위 폴더에서 다음 명령을 실행한다.

```powershell
python scripts/validate_public_release.py --expected-products 223
```

정상일 때 마지막 결과가 `PASS`이고 종료코드는 0이다. `ERROR`는 배포 차단 대상이고, `WARNING`은 자동으로 제외한 잘못된 후보 필드에 대한 참고사항이다.

## 릴리스 매니페스트 만들기

검증 오류가 없는 상태에서만 매니페스트를 만들 수 있다. 데이터 기준일은 등록대장의 기준일을 직접 입력한다.

```powershell
python scripts/validate_public_release.py `
  --expected-products 223 `
  --write-manifest data/release-manifest.json `
  --data-cutoff-date 2026-06-30
```

매니페스트에는 공개 JSON 두 파일의 SHA-256, 전체 PDF 묶음의 SHA-256, 제품·PDF 수, 자동 추출 요약 표시 수와 PDF 전용 수가 기록된다. PDF 또는 공개 JSON이 바뀌면 반드시 다시 생성한다.

## 커밋 전 최종 확인

```powershell
python -m unittest discover -s tests -p "test_*.py"
python scripts/validate_public_release.py `
  --expected-products 223 `
  --check-manifest data/release-manifest.json
```

GitHub Actions의 `Validate MSDS public release` 작업도 동일한 테스트와 매니페스트 검증을 실행한다. 공개 제품 수가 공식적으로 변경되면 명령과 워크플로의 `--expected-products` 값을 함께 변경한다.
