/* 응급조치(삼켰을 때)와 같은 MSDS 의 대응 문구를 나란히 보인다. 원문 문장은 바꾸지 않는다.
 *
 * 노루오토코팅 도료·희석제 14건은 원문 제2항에 H304(삼켜서 기도로 유입되면 치명적)와
 * 예방조치 P331(토하게 하지 마시오)가 있는데, 제4항 응급조치(먹었을 때)는 "구토를
 * 시키시오"다. 사이트가 잘못 읽은 것이 아니라 원문이 그렇다(2026-10-08 PDF 확인).
 * 공식 화면이라 "어긋난다·확인 중" 같은 말은 쓰지 않고, 그 MSDS 가 적은 삼켰을 때
 * 대응 문구(P301·P331)를 응급조치 바로 옆에 함께 싣는다. 공급사 확인은 관리대장
 * (관리자 화면)에서 한다. 같은 규칙을 scripts/audit_safety_consistency.py 가 쓴다.
 */
(function (global) {
  "use strict";

  // 삼켰을 때 구토를 시키라는 말. "구토를 시키지 말고" 같은 부정은 뺀다.
  const INDUCE_VOMIT = /(구토|토하)\S{0,3}\s*(유도|시키|일으키|하게\s*하|하도록)/;
  const NEGATED = /(유도|시키|일으키|하게\s*하|하도록)\S{0,4}\s*(지\s*마|지\s*말|말\s*것|않|금지|안\s*됨|안\s*된다|불가)/;
  const NO_VOMIT = [
    { code: "H304", label: "H304(삼켜서 기도로 유입되면 치명적)" },
    { code: "H314", label: "H314(피부에 심한 화상)" }
  ];

  function texts(value) {
    if (Array.isArray(value)) return value.map((item) => String(item || ""));
    if (value && typeof value === "object") return Object.values(value).flatMap(texts);
    return value ? [String(value)] : [];
  }

  /* hazards: H 문구 목록, precautions: 예방조치 묶음, ingestion: 응급조치(삼켰을 때) 문장 목록.
   * 어긋나면 { reasons: [...], sentence } 를, 아니면 null 을 돌려준다. */
  function vomitConflict({ hazards, precautions, ingestion } = {}) {
    const hazardText = texts(hazards).join(" ");
    const hasP331 = /P331/.test(texts(precautions).join(" "));
    const sentence = texts(ingestion)
      .flatMap((line) => line.split(/(?<=[.다오함])\s+/))
      .find((part) => INDUCE_VOMIT.test(part) && !NEGATED.test(part));
    if (!sentence) return null;
    const reasons = NO_VOMIT.filter((item) => hazardText.includes(item.code)).map((item) => item.label);
    if (hasP331) reasons.push("P331(토하게 하지 마시오)");
    return reasons.length ? { reasons, sentence: sentence.trim() } : null;
  }

  // 같은 MSDS 의 삼켰을 때 대응 문구(P301…, P331). 글은 원문 그대로다.
  function ingestionStatements(precautions) {
    return texts(precautions).filter((line) => /P301|P331/.test(line)).map((line) => line.trim());
  }

  global.MsdsSafety = { vomitConflict, ingestionStatements };
})(window);
