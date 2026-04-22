// Imperative toast system. Keeps deps nil (no react-toastify).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type ToastLevel = "info" | "success" | "warn" | "error";

type Toast = {
  id: number;
  level: ToastLevel;
  message: string;
  ttlMs: number;
};

type ToastContextValue = {
  push: (message: string, level?: ToastLevel, ttlMs?: number) => void;
  clear: () => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextIdRef = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback<ToastContextValue["push"]>(
    (message, level = "info", ttlMs = 4000) => {
      const id = nextIdRef.current++;
      setToasts((t) => [...t, { id, level, message, ttlMs }]);
    },
    [],
  );

  const clear = useCallback(() => setToasts([]), []);

  return (
    <ToastContext.Provider value={{ push, clear }}>
      {children}
      <div
        style={{
          position: "fixed",
          right: 20,
          bottom: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          zIndex: 100,
          maxWidth: 340,
        }}
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, toast.ttlMs);
    return () => window.clearTimeout(timer);
  }, [onDismiss, toast.ttlMs]);

  const color: Record<ToastLevel, string> = {
    info: "var(--accent)",
    success: "var(--ok)",
    warn: "var(--warn)",
    error: "var(--err)",
  };

  return (
    <div
      onClick={onDismiss}
      role="status"
      style={{
        padding: "10px 14px",
        background: "var(--bg-1)",
        border: `1px solid ${color[toast.level]}`,
        borderLeft: `4px solid ${color[toast.level]}`,
        borderRadius: "var(--r2)",
        color: "var(--text-0)",
        fontSize: 12,
        cursor: "pointer",
        boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
        animation: "triage4-toast-in 150ms ease-out",
      }}
    >
      {toast.message}
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside a <ToastProvider>");
  }
  return ctx;
}
