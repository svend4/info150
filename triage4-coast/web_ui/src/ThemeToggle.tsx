// Light/dark theme toggle.
// Reads/writes localStorage["theme"] and sets <html data-theme=...>.
// Defaults to OS preference (matchMedia prefers-color-scheme), or
// dark if the OS doesn't expose one.

import { useEffect, useState } from "react";

type Theme = "light" | "dark";
const KEY = "theme";

function initial(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
    if (window.matchMedia?.("(prefers-color-scheme: light)").matches) {
      return "light";
    }
  } catch { /* localStorage may be blocked in private mode */ }
  return "dark";
}

function apply(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem(KEY, theme); } catch { /* ignore */ }
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => {
    const t = initial();
    apply(t);
    return t;
  });

  useEffect(() => { apply(theme); }, [theme]);

  const next = theme === "dark" ? "light" : "dark";
  const icon = theme === "dark" ? "☀" : "☾";
  const label = theme === "dark" ? "light mode" : "dark mode";

  return (
    <button
      onClick={() => setTheme(next)}
      title={`switch to ${label}`}
      style={{
        padding: "6px 12px",
        background: "var(--surface-2)",
        color: "var(--text)",
        border: "1px solid var(--border)",
        borderRadius: 4,
        cursor: "pointer",
        fontSize: 13,
        fontFamily: "inherit",
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
      }}
    >
      <span style={{ fontSize: 14 }}>{icon}</span>
      {label}
    </button>
  );
}
