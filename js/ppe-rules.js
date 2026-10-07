/* 보호구 판별 규칙. 조회 화면 요약판과 관리요령이 같이 쓴다.
 *
 * 전에는 화면마다 규칙이 따로 있었고, 둘 다 엉뚱한 것을 그렸다.
 *  - 요약판은 한 문장을 보호구 하나로만 읽었다. "P280 보호장갑·보호의·보안경"
 *    이 보안경 하나가 되어 TC-317 에서 보호장갑이 빠졌다.
 *  - 종류를 못 읽은 문장("○ 착용할 보호구 :" 같은 제목 조각)에 보호복
 *    그림을 기본으로 붙였다. 원문에 없는 보호구를 그려 넣은 셈이다.
 *  - 관리요령은 "호흡"(호흡하기 쉬운 자세), "신체" 한 낱말로 골라
 *    응급조치 문장에도 마스크·보호복이 붙었다.
 *
 * 그래서 규칙은 이렇다.
 *  - 보호구 이름이 분명히 적힌 것만 그림으로 그린다. 낱말 하나("눈",
 *    "호흡", "신체")나 8항 소제목("눈 보호", "신체 보호")으로는 고르지 않는다.
 *    소제목 뒤에 "보호구가 필요하지 않음"이 오는 원문도 있다.
 *  - 한 문장에 여럿이 있으면 모두 그린다.
 *  - 화재 진압·구조자용 보호구는 작업자 보호구가 아니므로 뺀다.
 *  - 종류를 못 읽은 것은 그림 없이 둔다.
 */
(function (global) {
  "use strict";

  const RULES = [
    {
      key: "goggles",
      label: "보안경",
      purpose: "눈 자극·비산물 보호",
      words: ["보안경", "고글", "안면보호구", "보안면", "goggle", "safetyglasses", "faceshield"]
    },
    {
      key: "gloves",
      label: "보호장갑",
      purpose: "피부 접촉 저감",
      words: ["장갑", "glove"]
    },
    {
      key: "mask",
      label: "호흡보호구",
      purpose: "증기·분진 흡입 저감",
      words: ["마스크", "호흡보호구", "호흡용보호", "호흡기보호구", "방독", "공기호흡기", "respirator", "scba"]
    },
    {
      key: "suit",
      label: "보호복",
      purpose: "피부·의복 오염 방지",
      words: ["보호복", "보호의", "앞치마", "protectiveclothing", "apron"]
    },
    {
      key: "boots",
      label: "안전화",
      purpose: "발 보호·미끄럼 저감",
      words: ["안전화", "장화", "safetyshoes", "boots"]
    }
  ];

  // 호흡보호구는 원문이 종류를 하나로 적었으면 그 이름을 쓴다.
  const MASK_KINDS = [
    { words: ["방독"], label: "방독마스크", purpose: "유기증기·가스 흡입 방지" },
    { words: ["방진"], label: "방진마스크", purpose: "분진·미스트 흡입 방지" },
    { words: ["송기마스크", "공기호흡기", "에어라인", "scba"], label: "송기마스크", purpose: "산소결핍·고농도 작업 시 호흡 보호" }
  ];

  // 이 말이 든 문장은 화재 진압·구조자용이다. 작업자가 늘 쓰는 보호구가 아니다.
  const FIRE_CONTEXT = ["화재", "소화", "진압", "구조자", "소방"];

  // 원문 항목 제목. 이것만 남은 줄은 내용이 아니라 제목 조각이다.
  const HEADING_PHRASES = [
    "노출방지및개인보호구",
    "인체를보호하기위해필요한조치사항및보호구",
    "화재진압시착용할보호구및예방조치",
    "화재진압시착용할보호구및",
    "화재진압시착용할보호구",
    "착용할보호구및예방조치",
    "한조치사항및보호구",
    "조치사항및보호구",
    "착용할보호구",
    "개인보호구(ppe)",
    "개인보호구",
    "personalprecautionsandprotectiveequipment",
    "personalprecautions,protectiveequipment",
    "및보호구",
    "보호구"
  ];

  function normalize(value) {
    return String(value || "").toLowerCase().replace(/\s+/g, "");
  }

  function hasAny(normalized, words) {
    return words.some((word) => normalized.includes(word));
  }

  function isFireContext(text) {
    return hasAny(normalize(text), FIRE_CONTEXT);
  }

  // 줄 앞의 항목 번호·기호를 뗀다. "가.", "c.", "8.", "5.3.", "1)", "○", "Section 8 –"
  function stripMarkers(text) {
    return String(text || "")
      .replace(/^\s*(?:section\s*\d+\s*[–—:-]?\s*)/i, "")
      .replace(/^\s*(?:[-–—•·*○●◦□■]\s*)+/, "")
      .replace(/^\s*(?:\d+(?:\.\d+)*\.?|\d+\)|[가-하]\.|[a-zA-Z]\.)\s*/, "")
      .trim();
  }

  /* 제목 조각이면 "" 를, 아니면 앞의 제목을 떼고 남은 내용을 돌려준다.
   * "가. 인체를 보호하기 위해 필요한 조치사항 및 보호구 모든 점화원을 제거하시오"
   * → "모든 점화원을 제거하시오" */
  function cleanCandidate(value) {
    let text = stripMarkers(String(value || "").replace(/\s+/g, " ").trim());
    if (!text) return "";
    // 원문 제목을 앞에서 떼어 낸다. 띄어쓰기가 제각각이라 글자 단위로 맞춘다.
    for (const phrase of HEADING_PHRASES) {
      const pattern = new RegExp("^" + [...phrase].map((ch) => ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s*"), "i");
      if (pattern.test(text)) {
        text = text.replace(pattern, "").replace(/^\s*[:：\-–]\s*/, "").trim();
        break;
      }
    }
    text = stripMarkers(text);
    const rest = normalize(text).replace(/[^0-9a-z가-힣]/g, "");
    if (rest.length < 4) return "";
    if (/^자료없음/.test(rest)) return "";
    return text;
  }

  function maskDetail(normalized) {
    const kinds = MASK_KINDS.filter((kind) => hasAny(normalized, kind.words));
    return kinds.length === 1 ? kinds[0] : null;
  }

  /* 원문 8항이 한 덩어리로 들어온 줄이 있다. 그 안에 "화재" 한 마디가 섞였다고
   * 덩어리째 버리면 "연속 작업시 방독면 등을 착용한다" 같은 문장까지 잃는다.
   * 그래서 문장·항목 단위로 쪼갠 뒤에 화재 진압 문장만 뺀다. */
  function splitSentences(text) {
    return String(text || "")
      .split(/[.。!?;]\s*|\n+|\s(?=[가-하]\.)/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  /* 여러 원문 줄에서 보호구를 고른다. 차례는 RULES 순서로 고정한다.
   * 돌려주는 값: [{ key, label, purpose, file }] */
  function detect(texts) {
    const lines = (Array.isArray(texts) ? texts : [texts])
      .flatMap((item) => (Array.isArray(item) ? item : [item]))
      .flatMap(splitSentences)
      .filter((item) => !isFireContext(item));
    const joined = normalize(lines.join(" "));
    if (!joined) return [];
    return RULES.filter((rule) => hasAny(joined, rule.words)).map((rule) => {
      const kind = rule.key === "mask" ? maskDetail(joined) : null;
      return {
        key: rule.key,
        label: kind ? kind.label : rule.label,
        purpose: kind ? kind.purpose : rule.purpose,
        file: `assets/ppe/${rule.key}.svg`
      };
    });
  }

  /* 종류는 못 읽었지만 보호구를 쓰라는 내용은 있는 줄. 그림 없이 원문 확인만 권한다. */
  function hasUnspecifiedMention(texts) {
    return (Array.isArray(texts) ? texts : [texts])
      .map(cleanCandidate)
      .some((text) => text && !isFireContext(text) && normalize(text).includes("보호구"));
  }

  global.MsdsPpe = { RULES, detect, cleanCandidate, hasUnspecifiedMention, isFireContext };
})(window);
