from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PRODUCTS_PATH = ROOT / "data" / "msds.local.json"
LOCAL_OVERRIDES_PATH = ROOT / "data" / "msds-overrides.local.json"
PUBLIC_PRODUCTS_PATH = ROOT / "data" / "msds.public.json"
PUBLIC_OVERRIDES_PATH = ROOT / "data" / "msds-overrides.public.json"

PDF_PATH_FIELDS = ("pdfPath", "sourcePdfPath")
PDF_RELATIVE_FIELDS = ("relativePath", "sourceRelativePath")
MATCH_FIELDS = ("fileName", "relativePath")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def to_pdf_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    if text.startswith(("http://", "https://")):
        return text
    text = text.lstrip("/")
    if text.startswith("pdf/"):
        return text
    return f"pdf/{text}"


def to_pdf_relative_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    text = text.lstrip("/")
    if text.startswith("pdf/"):
        return text[4:]
    return text


def normalize_pdf_fields(item: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(item)

    for field in PDF_PATH_FIELDS:
        if result.get(field):
            result[field] = to_pdf_path(result[field])

    for field in PDF_RELATIVE_FIELDS:
        if result.get(field):
            result[field] = to_pdf_relative_path(result[field])

    match = result.get("match")
    if isinstance(match, dict):
        match = deepcopy(match)
        if match.get("relativePath"):
            match["relativePath"] = to_pdf_relative_path(match["relativePath"])
        result["match"] = match

    return result


def normalize_overrides(overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for override in overrides:
        item = normalize_pdf_fields(override)
        relative = item.get("sourceRelativePath") or item.get("match", {}).get("relativePath")
        if relative and not item.get("sourcePdfPath"):
            item["sourcePdfPath"] = to_pdf_path(relative)
        normalized.append(item)
    return normalized


def normalize_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("\\", "/").lstrip("/")


def build_override_lookup(overrides: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for override in overrides:
        match = override.get("match") if isinstance(override.get("match"), dict) else {}
        values = [
            match.get("fileName"),
            match.get("relativePath"),
            override.get("sourceRelativePath"),
            override.get("sourcePdfPath"),
        ]
        for value in values:
            key = normalize_key(value)
            if key:
                lookup.setdefault(key, override)
            if key.startswith("pdf/"):
                lookup.setdefault(key[4:], override)
    return lookup


def find_matching_override(product: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    values = [
        product.get("fileName"),
        product.get("relativePath"),
        product.get("sourceRelativePath"),
        product.get("pdfPath"),
        product.get("sourcePdfPath"),
    ]
    for value in values:
        key = normalize_key(value)
        if key in lookup:
            return lookup[key]
        if key.startswith("pdf/") and key[4:] in lookup:
            return lookup[key[4:]]
    return None


def normalize_products(products: list[dict[str, Any]], overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = build_override_lookup(overrides)
    normalized = []

    for product in products:
        item = normalize_pdf_fields(product)
        override = find_matching_override(item, lookup)
        override_relative = None
        if override:
            override_relative = override.get("sourceRelativePath") or override.get("match", {}).get("relativePath")

        if override_relative:
            item["relativePath"] = to_pdf_relative_path(override_relative)
            item["pdfPath"] = to_pdf_path(override_relative)
        elif item.get("relativePath"):
            item["pdfPath"] = to_pdf_path(item["relativePath"])
        elif item.get("pdfPath"):
            item["pdfPath"] = to_pdf_path(item["pdfPath"])
        elif item.get("fileName"):
            item["pdfPath"] = to_pdf_path(item["fileName"])

        normalized.append(item)

    return normalized


def coerce_list(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return data[key]
    raise ValueError(f"Expected a list or an object with '{key}'.")


def main() -> int:
    products_source = read_json(LOCAL_PRODUCTS_PATH)
    overrides_source = read_json(LOCAL_OVERRIDES_PATH)

    products = coerce_list(products_source, "products")
    overrides = coerce_list(overrides_source, "overrides")

    public_overrides = normalize_overrides(overrides)
    public_products = normalize_products(products, public_overrides)

    products_payload: Any
    if isinstance(products_source, dict):
        products_payload = deepcopy(products_source)
        products_payload["products"] = public_products
    else:
        products_payload = public_products

    overrides_payload: Any
    if isinstance(overrides_source, dict):
        overrides_payload = deepcopy(overrides_source)
        overrides_payload["overrides"] = public_overrides
    else:
        overrides_payload = public_overrides

    write_json(PUBLIC_PRODUCTS_PATH, products_payload)
    write_json(PUBLIC_OVERRIDES_PATH, overrides_payload)

    print("Public data build complete")
    print(f"- Products: {len(public_products)} -> {PUBLIC_PRODUCTS_PATH.relative_to(ROOT).as_posix()}")
    print(f"- Overrides: {len(public_overrides)} -> {PUBLIC_OVERRIDES_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
