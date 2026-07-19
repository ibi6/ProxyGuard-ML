/**
 * Resolve the saved color theme before CSS is requested to avoid a flash.
 * This file intentionally has no dependencies and remains compatible with CSP.
 */
(function bootstrapTheme() {
  "use strict";

  const STORAGE_KEY = "pg_theme";
  const VALID_PREFERENCES = new Set(["system", "light", "dark"]);
  const root = document.documentElement;
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)");

  function readPreference() {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      return VALID_PREFERENCES.has(saved) ? saved : "system";
    } catch (_) {
      return "system";
    }
  }

  let preference = readPreference();

  function resolveTheme() {
    return preference === "system"
      ? (systemDark.matches ? "dark" : "light")
      : preference;
  }

  function applyTheme(emitChange) {
    const theme = resolveTheme();
    root.dataset.theme = theme;
    root.dataset.themePreference = preference;
    root.style.colorScheme = theme;

    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) {
      themeColor.setAttribute("content", theme === "dark" ? "#08151e" : "#f2f6f7");
    }

    if (emitChange) {
      window.dispatchEvent(new CustomEvent("pg:themechange", {
        detail: { preference, theme },
      }));
    }
    return theme;
  }

  function setPreference(nextPreference) {
    if (!VALID_PREFERENCES.has(nextPreference)) return false;
    preference = nextPreference;
    try {
      window.localStorage.setItem(STORAGE_KEY, preference);
    } catch (_) {
      /* The selected theme still applies for this page session. */
    }
    applyTheme(true);
    return true;
  }

  function onSystemThemeChange() {
    if (preference === "system") applyTheme(true);
  }

  if (typeof systemDark.addEventListener === "function") {
    systemDark.addEventListener("change", onSystemThemeChange);
  } else if (typeof systemDark.addListener === "function") {
    systemDark.addListener(onSystemThemeChange);
  }

  applyTheme(false);
  window.pgTheme = Object.freeze({
    getPreference: () => preference,
    getResolvedTheme: resolveTheme,
    setPreference,
  });
}());
