// Thin keyboard-shortcut hook. Binds a map of shortcut → handler
// to the window `keydown` event. Shortcut syntax: lower-case keys
// joined by "+" — e.g. "j", "k", "?", "mod+s" (mod = cmd on macOS,
// ctrl elsewhere), "shift+j". Keystrokes inside <input>, <select>,
// <textarea>, or contenteditable are ignored so typing in a
// search box doesn't trigger shortcuts.

import { useEffect } from "react";

export type Hotkey = string;
export type HotkeyMap = Record<Hotkey, (event: KeyboardEvent) => void>;

function isEditable(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

function normalise(event: KeyboardEvent): string {
  const key = event.key.toLowerCase();
  const parts: string[] = [];
  if (event.ctrlKey || event.metaKey) parts.push("mod");
  if (event.shiftKey && key !== "shift") parts.push("shift");
  if (event.altKey && key !== "alt") parts.push("alt");
  // Ignore pure modifier key events.
  if (["control", "meta", "shift", "alt"].includes(key)) return "";
  parts.push(key);
  return parts.join("+");
}

export function useHotkeys(map: HotkeyMap, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const handler = (e: KeyboardEvent) => {
      if (isEditable(e.target)) return;
      const combo = normalise(e);
      if (!combo) return;
      const fn = map[combo];
      if (fn) {
        e.preventDefault();
        fn(e);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [map, enabled]);
}
