import type { ReactNode } from "react";

import TopBar, { type TabKey } from "./TopBar";

type Props = {
  tab: TabKey;
  onTabChange: (tab: TabKey) => void;
  children: ReactNode;
};

export default function AppLayout({ tab, onTabChange, children }: Props) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        background: "var(--bg-0)",
      }}
    >
      <TopBar active={tab} onChange={onTabChange} />
      <main style={{ flex: 1, padding: 20 }}>{children}</main>
      <footer
        style={{
          padding: "10px 20px",
          borderTop: "1px solid var(--border-1)",
          color: "var(--text-2)",
          fontSize: 11,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span>
          triage4 · research decision-support. Not a certified medical device.
        </span>
        <span style={{ fontFamily: "var(--font-mono)" }}>v0.2</span>
      </footer>
    </div>
  );
}
