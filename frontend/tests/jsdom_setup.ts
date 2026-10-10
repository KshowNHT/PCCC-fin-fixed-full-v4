import { JSDOM } from "jsdom";
const dom = new JSDOM("<!DOCTYPE html><html><body><div id='root'></div></body></html>", { url: "http://localhost/", pretendToBeVisual: true });
const g: any = globalThis;
g.window = dom.window; g.document = dom.window.document;
for (const k of ["HTMLElement", "Element", "Node", "MouseEvent", "Event", "getComputedStyle", "requestAnimationFrame", "cancelAnimationFrame", "MutationObserver", "SVGElement"]) {
  if (!(k in g) || k === "navigator") g[k] = (dom.window as any)[k];
}
try { Object.defineProperty(g, "navigator", { value: dom.window.navigator, configurable: true }); } catch {}
g.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
g.IS_REACT_ACT_ENVIRONMENT = true;
g.localStorage = dom.window.localStorage;
(dom.window as any).HTMLElement.prototype.scrollIntoView = function () {};
(dom.window as any).HTMLElement.prototype.scrollTo = function () {};
(dom.window as any).Element.prototype.scrollTo = function () {};
(dom.window as any).matchMedia = (dom.window as any).matchMedia || ((q: string) => ({ matches: false, media: q, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
g.matchMedia = (dom.window as any).matchMedia;
