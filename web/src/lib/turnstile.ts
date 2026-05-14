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
let backdropEl: HTMLDivElement | null = null;
let containerEl: HTMLDivElement | null = null;
let widgetId: string | null = null;

interface TurnstileGlobal {
  render: (
    el: HTMLElement,
    opts: {
      sitekey: string;
      callback: (token: string) => void;
      "error-callback"?: (code?: string) => void;
      "expired-callback"?: () => void;
      "before-interactive-callback"?: () => void;
      "after-interactive-callback"?: () => void;
      // "invisible" was removed from Cloudflare's Turnstile API. To get
      // an effectively invisible widget you use a normal size + the
      // "interaction-only" appearance, which renders nothing when
      // Cloudflare's heuristics resolve the challenge silently.
      size?: "normal" | "compact" | "flexible";
      appearance?: "always" | "execute" | "interaction-only";
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
  if (containerEl && backdropEl) return containerEl;

  // Dimmed full-screen backdrop. Hidden by default — only shown while
  // Cloudflare is actually displaying a visible challenge.
  const backdrop = document.createElement("div");
  backdrop.style.position = "fixed";
  backdrop.style.inset = "0";
  backdrop.style.background = "rgba(0, 0, 0, 0.45)";
  backdrop.style.zIndex = "9998";
  backdrop.style.display = "none";
  backdrop.style.alignItems = "center";
  backdrop.style.justifyContent = "center";

  // Centered widget host. Reserve the standard 300×65 Turnstile widget
  // footprint so the checkbox has room to render when a challenge fires.
  const el = document.createElement("div");
  el.style.width = "300px";
  el.style.height = "65px";
  el.style.zIndex = "9999";

  backdrop.appendChild(el);
  document.body.appendChild(backdrop);
  backdropEl = backdrop;
  containerEl = el;
  return el;
}

function showBackdrop() {
  if (backdropEl) backdropEl.style.display = "flex";
}

function hideBackdrop() {
  if (backdropEl) backdropEl.style.display = "none";
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
      // "interaction-only" + execute renders zero pixels unless Cloudflare
      // decides the user needs to actively pass a challenge. When a visible
      // challenge IS required, `before-interactive-callback` fires and we
      // reveal the modal backdrop so the centered checkbox is unmissable.
      appearance: "interaction-only",
      execution: "execute",
      callback: (token: string) => {
        hideBackdrop();
        resolve(token);
      },
      "error-callback": (code?: string) => {
        hideBackdrop();
        console.error("[turnstile] error-callback", code);
        reject(new Error(`Turnstile challenge failed${code ? ` (${code})` : ""}`));
      },
      "expired-callback": () => {
        hideBackdrop();
        reject(new Error("Turnstile token expired"));
      },
      "before-interactive-callback": () => showBackdrop(),
      "after-interactive-callback": () => hideBackdrop(),
    });

    // Defer execute() one tick so the widget has finished mounting its
    // iframe — calling it synchronously after render() occasionally
    // no-ops on the first invocation.
    setTimeout(() => {
      try {
        window.turnstile!.execute(widgetId!);
      } catch (e) {
        reject(e instanceof Error ? e : new Error(String(e)));
      }
    }, 0);
  });
}
