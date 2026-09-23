"""원본 PDF 를 다시 읽어 사이트 값과 대조하고, 확인된 보완을 적어 둔다.

    py scripts/repair_from_pdf.py                    대조 결과만 보기(아무것도 안 바꿈)
    py scripts/repair_from_pdf.py --write            data/msds-content-repairs.json 에 보완을 적기
    py scripts/repair_from_pdf.py --write-register   원문과 다른 날짜를 관리대장에 적고 이력을 남기기

모든 제품에 같은 규칙(scripts/msds_pdf_text.py)을 쓴다. 원문에 없는 것은 넣지 않는다.

  응급조치   지금 빈 칸(눈·피부·흡입·섭취·의사 주의사항)만 원문 4항에서 채운다. 있는 칸은
             건드리지 않는다. 성분표 줄·다른 항목의 조치가 딸려 온 칸은 버린다.
  성분 이름  "번호", "황화수소 0.05" 처럼 깨진 이름만 원문 3항의 같은 CAS 줄 이름으로 바꾼다.
  유해문구   원문 2항에서 읽은 H코드가 사이트 H코드를 모두 품고 더 많을 때만(사이트가
             일부를 빠뜨린 것) 원문 목록으로 바꾼다. 그림문자·신호어는 건드리지 않는다.
  긴급전화   사이트 번호가 MSDS 번호의 조각이면(옆 칸 값이 딸려 온 것) 원문 1항에서 다시 읽는다.
  날짜       원문 최종 개정일(개정 이력이 줄줄이 적혔으면 가장 늦은 날)과 최초 작성일을
             사이트 값과 대 본다. 관리대장에 적을 때는 그 PDF 의 SHA-256 을 같이 적어,
             나중에 같은 자리에 새 PDF 가 들어오면 옛 날짜를 덮어쓰지 않게 한다.

실행이 끝나면 다시 사이트 데이터를 만들 때 normalize_public_content.py 와
apply_msds_register.py 가 이 결과를 반영한다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import warnings
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.CRITICAL)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import msds_pdf_text as T  # noqa: E402
import normalize_public_content as N  # noqa: E402
from repair_ingredient_rows import is_junk_name, unusable_source  # noqa: E402

PRODUCTS_PATH = ROOT / "data" / "msds.public.json"
REGISTER_PATH = ROOT / "data" / "msds-register.json"
REPAIRS_PATH = ROOT / "data" / "msds-content-repairs.json"
AID_KEYS = ("eye", "skin", "inhalation", "ingestion", "note")
LABEL_NAME = re.compile(r"^(?:번호|CAS|물질명|이명|관용명)?$")
NO_DATA = re.compile(r"자료\s*없음|해당\s*없음")


def broken_name(name: str, content: str = "") -> bool:
    """표 머리글이 이름 칸에 들어갔거나, 옆 칸("자료없음", 함유량)이 딸려 온 이름.

    "C.I. pigment blue 60", "IRGAFOS 168" 처럼 숫자로 끝나는 진짜 이름은 걸리지 않게,
    끝 숫자가 그 행의 함유량과 같을 때만 딸려 온 것으로 본다.
    """
    name = str(name or "").strip()
    if LABEL_NAME.match(name) or NO_DATA.search(name):
        return True
    tail = re.search(r"\s(\d+(?:\.\d+)?)%?$", name)
    amounts = re.findall(r"\d+(?:\.\d+)?", str(content or ""))
    return bool(tail and tail.group(1) in amounts)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def statement_codes(lines: list[str]) -> list[str]:
    probe = {"hazardStatements": list(lines or [])}
    N.normalize_statements(probe)
    return N._codes(probe["hazardStatements"])


def examine(product: dict, today: str) -> dict:
    path = ROOT / product["pdfPath"]
    pages = T.page_texts(path)
    text = "\n".join(pages)
    junk = T.boilerplate(pages)
    lines = text.splitlines()
    found: dict = {"id": product["id"], "name": product["productName"]}

    # 응급조치: 빈 칸만
    current = product.get("firstAid") or {}
    section4 = T.section(lines, 4)
    parsed = T.parse_first_aid(section4, junk) if section4 else {}
    fill = {}
    for key in AID_KEYS:
        if current.get(key) or key not in parsed:
            continue
        items = T.usable_first_aid(key, parsed[key])
        if items:
            fill[key] = items
    if fill:
        found["firstAid"] = {"fill": fill, "pdf": product["pdfPath"], "checkedOn": today}

    # 성분 이름: 깨진 것만
    section3 = T.section(lines, 3)
    rows = {r["casNo"]: r for r in (T.parse_ingredients(section3, junk) if section3 else [])}
    names = []
    for index, row in enumerate(product.get("ingredients") or []):
        name = str(row.get("chemicalName") or "").strip()
        if not broken_name(name, row.get("content", "")):
            continue
        source = rows.get(str(row.get("casNo") or "").strip(), {}).get("sourceName", "")
        if source and not is_junk_name(source) and not unusable_source(source, "") and not broken_name(source, row.get("content", "")):
            names.append({"productId": product["id"], "index": index, "cas": row.get("casNo"),
                          "before": row.get("chemicalName"), "after": source, "checkedOn": today})
        else:
            names.append({"productId": product["id"], "index": index, "cas": row.get("casNo"),
                          "before": row.get("chemicalName"), "after": "", "unresolved": True})
    if names:
        found["ingredientNames"] = names

    # 유해·위험문구: 사이트가 일부를 빠뜨렸을 때만
    if not product.get("hazardNotClassified"):
        section2 = T.section(lines, 2)
        pdf_lines, _ = T.parse_statements(section2, junk) if section2 else ([], {})
        pdf_codes = N._codes(pdf_lines)
        site_codes = statement_codes(product.get("hazardStatements") or [])
        if site_codes and set(site_codes) < set(pdf_codes):
            found["hazardStatements"] = {"beforeCodes": site_codes, "after": pdf_lines, "pdf": product["pdfPath"],
                                         "added": sorted(set(pdf_codes) - set(site_codes)), "checkedOn": today}
        elif pdf_codes and site_codes and set(pdf_codes) != set(site_codes):
            found["codesDiffer"] = {"siteOnly": sorted(set(site_codes) - set(pdf_codes)),
                                    "pdfOnly": sorted(set(pdf_codes) - set(site_codes))}

    # 긴급전화번호: 사이트 번호가 MSDS 번호의 조각일 때만(옆 칸 값이 딸려 온 것) 원문에서 다시 읽는다.
    contact = str(product.get("emergencyContact") or "")
    msds_digits = re.sub(r"\D", "", str(product.get("msdsNo") or ""))
    groups = [re.sub(r"\D", "", g) for g in re.findall(r"\d[\d\s-]{4,}\d", contact)]
    if msds_digits and groups and all(g in msds_digits for g in groups):
        phone = T.emergency_phone(pages)
        if phone:
            found["emergencyContact"] = {"before": contact, "after": phone, "pdf": product["pdfPath"], "checkedOn": today}

    # 날짜
    revision = T.revision_date(text)
    issue = T.issue_date(text)
    site_revision = str(product.get("revisionDate") or "")
    if revision and revision != site_revision:
        if not site_revision or revision > site_revision:
            found["revisionDate"] = {"site": site_revision, "pdf": revision}
        else:
            found["revisionLater"] = {"site": site_revision, "pdf": revision}   # 원문보다 사이트가 늦음. 손으로 볼 것
    if issue and issue != product.get("issueDate"):
        found["issueDate"] = {"site": product.get("issueDate", ""), "pdf": issue}
    if revision and revision == site_revision:
        found["revisionConfirmed"] = True
    if "revisionDate" in found or "issueDate" in found or found.get("revisionConfirmed"):
        found["sha256"] = sha256(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--write-register", action="store_true")
    args = parser.parse_args()

    today = date.today().isoformat()
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    results = []
    for product in products:
        try:
            results.append(examine(product, today))
        except Exception as error:   # 읽히지 않는 PDF 는 건너뛰고 알린다
            results.append({"id": product["id"], "name": product["productName"], "error": str(error)})

    aid = [r for r in results if "firstAid" in r]
    names = [n for r in results for n in r.get("ingredientNames", [])]
    hazards = [r for r in results if "hazardStatements" in r]
    revisions = [r for r in results if "revisionDate" in r]
    issues = [r for r in results if "issueDate" in r]
    print(f"응급조치 빈 칸을 원문에서 채울 수 있음  {len(aid)}건 ({sum(len(r['firstAid']['fill']) for r in aid)}칸)")
    print(f"깨진 성분 이름                       {len(names)}행 (원문 이름 있음 {sum(1 for n in names if n['after'])})")
    print(f"유해·위험문구가 원문보다 적음          {len(hazards)}건")
    for r in hazards:
        print(f"    {r['name'][:30]}: {', '.join(r['hazardStatements']['added'])} 빠짐")
    print(f"H코드가 원문과 달라 손으로 볼 것      {sum(1 for r in results if 'codesDiffer' in r)}건")
    print(f"개정일이 원문과 다름                  {len(revisions)}건 / 최초 작성일이 원문과 다름 {len(issues)}건")
    for r in results:
        if "revisionLater" in r:
            print(f"    사이트 개정일이 원문보다 늦어 두었음: {r['name'][:30]} 사이트 {r['revisionLater']['site']} 원문 {r['revisionLater']['pdf']}")
    print(f"PDF 를 못 읽음                        {sum(1 for r in results if 'error' in r)}건")

    contacts = [r for r in results if "emergencyContact" in r]
    print(f"긴급전화번호가 MSDS 번호 조각으로 들어감  {len(contacts)}건")
    for r in contacts:
        print(f"    {r['name'][:30]}: {r['emergencyContact']['before']} → {r['emergencyContact']['after']}")

    if args.write:
        # 이미 반영된 보완은 지금 데이터에서 다시 찾아지지 않는다(빈 칸이 이미 채워졌으므로).
        # 집 PC 가 로컬 데이터로 다시 만들 때도 반영돼야 하니 지우지 않고 합친다.
        old = json.loads(REPAIRS_PATH.read_text(encoding="utf-8")) if REPAIRS_PATH.exists() else {}
        first_aid = dict(old.get("firstAid") or {})
        for r in aid:
            kept = first_aid.get(r["id"], {"fill": {}})
            kept["fill"] = {**r["firstAid"]["fill"], **kept.get("fill", {})}
            first_aid[r["id"]] = {**r["firstAid"], "fill": kept["fill"]}
        seen = {(n["productId"], n["index"], n["cas"], n["before"]) for n in old.get("ingredientNames") or []}
        ingredient_names = list(old.get("ingredientNames") or []) + [
            n for n in names if n["after"] and (n["productId"], n["index"], n["cas"], n["before"]) not in seen]
        repairs = {
            "about": "원본 PDF 를 다시 읽어 확인한 보완. scripts/repair_from_pdf.py 가 만들고 "
                     "scripts/normalize_public_content.py 가 사이트 데이터를 만들 때마다 반영한다.",
            "generatedOn": today,
            "firstAid": first_aid,
            "ingredientNames": ingredient_names,
            "hazardStatements": {**(old.get("hazardStatements") or {}), **{r["id"]: r["hazardStatements"] for r in hazards}},
            "emergencyContact": {**(old.get("emergencyContact") or {}), **{r["id"]: r["emergencyContact"] for r in contacts}},
        }
        with REPAIRS_PATH.open("w", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(repairs, ensure_ascii=False, indent=2) + "\n")
        print(f"적었다: {REPAIRS_PATH.relative_to(ROOT).as_posix()}")

    if args.write_register:
        register = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))
        entries = register["products"]
        by_id = {p["id"]: p for p in products}
        history = register.setdefault("history", [])
        count = 0
        for r in revisions + [x for x in issues if x not in revisions]:
            entry = entries.get(r["id"])
            if entry is None:
                continue
            product = by_id[r["id"]]
            notes = []
            if "revisionDate" in r:
                entry["revisionDate"] = r["revisionDate"]["pdf"]
                notes.append("원문 최종 개정일(개정 이력이 여럿이면 가장 늦은 날)")
            if "issueDate" in r:
                entry["issueDate"] = r["issueDate"]["pdf"]
                notes.append(f"원문 최초 작성일 {r['issueDate']['pdf']} (사이트 {r['issueDate']['site'] or '없음'})")
            entry["datesCheckedSha256"] = r["sha256"]
            history.append({
                "date": today, "action": "날짜 바로잡음",
                "productName": product["productName"], "supplier": entry.get("supplier", product.get("supplier", "")),
                "oldId": r["id"], "newId": r["id"], "oldFile": product["pdfPath"], "newFile": product["pdfPath"],
                "oldMsdsNo": product.get("msdsNo", ""), "newMsdsNo": product.get("msdsNo", ""),
                "oldRevision": product.get("revisionDate", ""),
                "newRevision": r.get("revisionDate", {}).get("pdf", product.get("revisionDate", "")),
                "source": "원본 PDF 대조", "sha256": r["sha256"], "note": "; ".join(notes),
            })
            count += 1
        # 사이트 개정일이 원문과 이미 같은 제품은 확인했다는 표시(그 PDF 의 해시)만 남긴다.
        confirmed = 0
        for r in results:
            entry = entries.get(r["id"])
            if entry is not None and r.get("revisionConfirmed") and entry.get("datesCheckedSha256") != r["sha256"]:
                entry["datesCheckedSha256"] = r["sha256"]
                confirmed += 1
        with REGISTER_PATH.open("w", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(register, ensure_ascii=False, indent=2) + "\n")
        print(f"관리대장에 날짜 {count}건을 적고 이력을 남겼다. 원문과 같음을 확인한 {confirmed}건에 PDF 해시를 적었다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
