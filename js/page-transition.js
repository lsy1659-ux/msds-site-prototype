/* 화면끼리 넘어갈 때 흰 번쩍임 없애기.
 *
 * 크롬 126 이상은 CSS 의 @view-transition 만 적어 두면 브라우저가 두
 * 문서를 겹쳐 넘겨 준다. 그런데 현장에서 쓰는 폰은 삼성 인터넷이나
 * 조금 지난 크롬인 경우가 많고, 그런 기기에서는 그 기능이 없어서 PC
 * 에서는 부드럽던 것이 폰에서는 흰 화면이 한 번 번쩍인다.
 *
 * 그래서 그 기능이 없는 기기에서만 같은 느낌을 손으로 낸다. 나갈 때
 * 잠깐 흐려지고, 새 화면이 뜨면서 밝아진다.
 */

(function () {
  "use strict";

  const root = document.documentElement;
  const prefersReduced = () =>
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // pagereveal 은 문서끼리 겹쳐 넘기는 기능과 같이 들어왔다. 이것이 있으면
  // 브라우저가 알아서 하므로 여기서는 손대지 않는다.
  const browserHandlesIt = "onpagereveal" in window;

  if (browserHandlesIt || prefersReduced()) return;

  root.classList.add("page-fade-in");
  window.setTimeout(() => root.classList.remove("page-fade-in"), 260);

  // 뒤로 가기로 돌아오면 흐린 채로 남을 수 있다. 되돌려 둔다.
  window.addEventListener("pageshow", () => root.classList.remove("page-fade-out"));

  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    const link = event.target instanceof Element
      ? event.target.closest("a.top-bar-tab[href], a.label-back[href], a.header-home-link[href]")
      : null;
    if (!link || link.target === "_blank") return;

    let url;
    try {
      url = new URL(link.getAttribute("href"), window.location.href);
    } catch (error) {
      return;
    }
    if (url.origin !== window.location.origin) return;
    if (url.href === window.location.href) return;

    event.preventDefault();

    // 넘어가는 일을 먼저 예약한다. 뒤에서 무엇이 잘못되어도 화면은 넘어간다.
    // 링크를 가로채는 방식이라 여기서 막히면 탭이 죽은 것처럼 보인다.
    window.setTimeout(() => { window.location.href = url.href; }, 150);

    // 넘어가지 못하고 이 화면에 남는 경우에도 흐린 채로 굳지 않게 되돌린다.
    window.setTimeout(() => root.classList.remove("page-fade-out"), 900);

    root.classList.add("page-fade-out");
  });
})();
