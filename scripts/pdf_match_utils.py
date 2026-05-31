"""Shared scoring helpers for local MSDS PDF matching reports."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
STRONG_THRESHOLD = 90
PROBABLE_THRESHOLD = 60
WEAK_THRESHOLD = 30


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\.pdf$", "", text)
    return re.sub(r"[\s()[\]{}<>_\-/\\.,:;]+", "", text)


def tokenize(value: Any) -> set[str]:
    tokens = re.split(r"[\s()[\]{}<>_\-/\\.,:;]+", str(value or "").lower())
    return {
        token
        for token in tokens
        if len(token) >= 2 and token not in {"msds", "sds", "pdf", "2020", "2021", "2022", "2023", "2024", "2025"}
    }


def similarity(left: Any, right: Any) -> float:
    a = normalize_text(left)
    b = normalize_text(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    shorter, longer = sorted((a, b), key=len)
    if len(shorter) >= 4 and shorter in longer:
        return len(shorter) / len(longer)
    return SequenceMatcher(None, a, b).ratio()


def strong_similarity(left: Any, right: Any, minimum: float = 0.82) -> bool:
    return similarity(left, right) >= minimum


def confidence_from_score(score: int) -> str:
    if score >= STRONG_THRESHOLD:
        return "strong_match_candidate"
    if score >= PROBABLE_THRESHOLD:
        return "probable_match_candidate"
    if score >= WEAK_THRESHOLD:
        return "weak_match_candidate"
    return "low_confidence"


def product_cas_numbers(product: dict[str, Any]) -> set[str]:
    ingredients = product.get("ingredients")
    if not isinstance(ingredients, list):
        ingredients = product.get("components")
    if not isinstance(ingredients, list):
        return set()
    return {
        cas
        for ingredient in ingredients
        if isinstance(ingredient, dict)
        for cas in CAS_RE.findall(str(ingredient.get("casNo") or ""))
    }


def product_match_terms(product: dict[str, Any]) -> dict[str, Any]:
    file_name = str(product.get("fileName") or "").strip()
    product_name = str(product.get("productName") or "").strip()
    erp_name = str(product.get("erpName") or "").strip()
    msds_no = str(product.get("msdsNo") or "").strip()
    supplier = str(product.get("supplier") or "").strip()
    return {
        "id": str(product.get("id") or ""),
        "fileName": file_name,
        "normalizedFileName": normalize_text(file_name),
        "productName": product_name,
        "normalizedProductName": normalize_text(product_name),
        "erpName": erp_name,
        "normalizedErpName": normalize_text(erp_name),
        "msdsNo": msds_no,
        "normalizedMsdsNo": normalize_text(msds_no),
        "supplier": supplier,
        "normalizedSupplier": normalize_text(supplier),
        "casNumbers": product_cas_numbers(product),
    }


def score_pdf_candidate(
    product: dict[str, Any],
    pdf: dict[str, Any],
    *,
    mapped: bool = False,
) -> dict[str, Any]:
    terms = product_match_terms(product)
    pdf_file_name = str(pdf.get("fileName") or "").strip()
    pdf_normalized_file = normalize_text(pdf.get("normalizedFileName") or pdf_file_name)
    pdf_text = normalize_text(pdf.get("normalizedText") or "")
    pdf_product_names = [str(value) for value in pdf.get("productNameCandidates") or []]
    pdf_msds_numbers = [str(value) for value in pdf.get("msdsNoCandidates") or []]
    pdf_cas_numbers = set(pdf.get("casNoCandidates") or pdf.get("casNumbers") or [])

    score = 0
    reasons: list[str] = []

    if terms["fileName"] and terms["fileName"] == pdf_file_name:
        score += 100
        reasons.append("exact_file_match")
    elif terms["normalizedFileName"] and terms["normalizedFileName"] == pdf_normalized_file:
        score += 90
        reasons.append("normalized_filename_match")

    if mapped:
        score += 100
        reasons.append("mapped")

    if terms["productName"]:
        if any(strong_similarity(terms["productName"], candidate) for candidate in pdf_product_names):
            score += 60
            reasons.append("product_name_strong")
        elif len(terms["normalizedProductName"]) >= 6 and terms["normalizedProductName"] in pdf_text:
            score += 60
            reasons.append("product_name_strong")

    if terms["erpName"]:
        if any(strong_similarity(terms["erpName"], candidate) for candidate in pdf_product_names):
            score += 50
            reasons.append("erp_name_strong")
        elif len(terms["normalizedErpName"]) >= 6 and terms["normalizedErpName"] in pdf_text:
            score += 50
            reasons.append("erp_name_strong")

    if terms["normalizedMsdsNo"]:
        pdf_msds_normalized = {normalize_text(value) for value in pdf_msds_numbers}
        if terms["normalizedMsdsNo"] in pdf_msds_normalized or terms["normalizedMsdsNo"] in pdf_text:
            score += 50
            reasons.append("msds_no_match")

    cas_overlap = sorted(terms["casNumbers"].intersection(pdf_cas_numbers))
    if len(cas_overlap) >= 2:
        score += 40
        reasons.append("cas_2plus_match")
    elif len(cas_overlap) == 1:
        score += 15
        reasons.append("cas_single_match")

    if terms["normalizedSupplier"] and len(terms["normalizedSupplier"]) >= 4 and terms["normalizedSupplier"] in pdf_text:
        score += 20
        reasons.append("supplier_match")

    product_tokens = tokenize(terms["fileName"]) | tokenize(terms["productName"]) | tokenize(terms["erpName"])
    pdf_tokens = tokenize(pdf_file_name)
    common_tokens = sorted(product_tokens.intersection(pdf_tokens))
    if len(common_tokens) >= 2:
        score += 20
        reasons.append("filename_keyword_match")

    has_non_cas_signal = any(reason != "cas_single_match" for reason in reasons)
    cas_only_single = reasons == ["cas_single_match"]
    confidence = confidence_from_score(score)
    include = score >= WEAK_THRESHOLD and not cas_only_single and has_non_cas_signal

    return {
        "fileName": pdf_file_name,
        "relativePath": pdf.get("relativePath", pdf_file_name),
        "score": score,
        "confidence": confidence,
        "reasons": reasons,
        "casOverlapCount": len(cas_overlap),
        "casOnlyWeak": cas_only_single,
        "include": include,
    }


def is_strong_or_probable(candidate: dict[str, Any]) -> bool:
    return candidate.get("confidence") in {"strong_match_candidate", "probable_match_candidate"}
