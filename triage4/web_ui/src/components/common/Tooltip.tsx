// Lightweight tooltip primitive. Hover / focus triggers a tiny
// fixed-position floating label. Used to gloss technical terms
// (ESS, HMT, R², SaMD, …) without forcing the reader off-page.

import { useRef, useState, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  text: string;
  width?: number;
};

export default function Tooltip({ children, text, width = 240 }: Props) {
  const [visible, setVisible] = useState(false);
  const [pos, setPos] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const ref = useRef<HTMLSpanElement>(null);

  const show = () => {
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    setPos({ x: rect.left + rect.width / 2, y: rect.top });
    setVisible(true);
  };

  return (
    <span
      ref={ref}
      tabIndex={0}
      onMouseEnter={show}
      onMouseLeave={() => setVisible(false)}
      onFocus={show}
      onBlur={() => setVisible(false)}
      style={{
        borderBottom: "1px dashed var(--text-2)",
        cursor: "help",
      }}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          style={{
            position: "fixed",
            left: Math.max(12, pos.x - width / 2),
            top: pos.y - 8,
            transform: "translateY(-100%)",
            width,
            padding: 8,
            background: "var(--bg-3)",
            color: "var(--text-0)",
            border: "1px solid var(--border-2)",
            borderRadius: "var(--r1)",
            fontSize: 11,
            fontFamily: "inherit",
            fontWeight: 400,
            textTransform: "none",
            letterSpacing: "normal",
            pointerEvents: "none",
            zIndex: 1000,
            boxShadow: "0 8px 20px rgba(0,0,0,0.45)",
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
}
