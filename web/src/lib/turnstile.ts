/**
 * Cloudflare Turnstile loader + token resolver.
 *
 * Loads the Turnstile JS once, renders an invisible widget on first call,
 * and resolves with a fresh token. Returns "" if no site key is configured
 * (dev mode), which the API will accept iff TURNSTILE_SECRET is also empty.
 */

const TURNSTILE_SRC =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=__turnstileOnLoad";

let loadPromise: Promise<void> | null = null;
let containerEl: HTMLDivElement | null = null;
let widgetId: string | null = null;

interface TurnstileGlobal {
  render: (
    el: HTMLElement,
    opts: {
      sitekey: string;
      callback: (token: string) => void;
      "error-callback"?: () => void;
      "expired-callback"?: () => void;
      size?: "normal" | "compact" | "invisible";
      execution?: "render" | "execute";
    },
  ) => string;
  execute: (widgetId: string) => void;
  reset: (widgetId: string) => void;
  remove: (widgetId: string) => void;
}

declare global {
  interface Window {
    turnstile?: TurnstileGlobal;
    __turnstileOnLoad?: () => void;
  }
}

function loadTurnstile(): Promise<void> {
  if (loadPromise) return loadPromise;
  loadPromise = new Promise<void>((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("Turnstile can only run in the browser"));
      return;
    }
    if (window.turnstile) {
      resolve();
      return;
    }

    window.__turnstileOnLoad = () => resolve();

    const script = document.createElement("script");
    script.src = TURNSTILE_SRC;
    script.async = true;
    script.defer = true;
    script.onerror = () => reject(new Error("Failed to load Turnstile script"));
    document.head.appendChild(script);
  });
  return loadPromise;
}

function ensureContainer(): HTMLDivElement {
  if (containerEl) return containerEl;
  const el = document.createElement("div");
  el.style.position = "fixed";
  el.style.bottom = "16px";
  el.style.right = "16px";
  el.style.zIndex = "9999";
  document.body.appendChild(el);
  containerEl = el;
  return el;
}

/**
 * Get a fresh Turnstile token. Returns "" if no site key is configured.
 *
 * On most page loads Turnstile resolves invisibly via Cloudflare heuristics.
 * If the user is challenged, a small widget appears bottom-right.
 */
export async function getTurnstileToken(): Promise<string> {
  const sitekey = process.env.NEXT_PUBLIC_TURNSTILE_SITEKEY ?? "";
  if (!sitekey) return "";

  await loadTurnstile();
  if (!window.turnstile) return "";

  const container = ensureContainer();

  return new Promise<string>((resolve, reject) => {
    if (widgetId !== null) {
      try {
        window.turnstile!.reset(widgetId);
      } catch {
        widgetId = null;
      }
    }

    widgetId = window.turnstile!.render(container, {
      sitekey,
      size: "invisible",
      execution: "execute",
      callback: (token: string) => resolve(token),
      "error-callback": () =>
        reject(new Error("Turnstile challenge failed")),
      "expired-callback": () =>
        reject(new Error("Turnstile token expired")),
    });

    try {
      window.turnstile!.execute(widgetId);
    } catch (e) {
      reject(e instanceof Error ? e : new Error(String(e)));
    }
  });
}
