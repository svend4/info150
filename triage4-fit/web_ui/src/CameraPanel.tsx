import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };

function lrImbalance(canvas: HTMLCanvasElement): number {
  const ctx = canvas.getContext("2d");
  if (!ctx) return 0;
  const { width, height } = canvas;
  const half = Math.floor(width / 2);
  const left = ctx.getImageData(0, 0, half, height).data;
  const right = ctx.getImageData(half, 0, width - half, height).data;
  const lum = (px: Uint8ClampedArray) => {
    let s = 0; let n = 0;
    for (let i = 0; i < px.length; i += 4) {
      s += 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
      n++;
    }
    return n ? s / n : 0;
  };
  const lL = lum(left); const lR = lum(right);
  const denom = (lL + lR) / 2 || 1;
  return Math.min(1, Math.abs(lL - lR) / denom);
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const [streaming, setStreaming] = useState(false);
  const [liveImbalance, setLiveImbalance] = useState<number>(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [exercise, setExercise] = useState<string>("squat");
  const [reps, setReps] = useState<number>(5);

  useEffect(() => {
    (async () => {
      try {
        const ds = await navigator.mediaDevices.enumerateDevices();
        const cams = ds
          .filter((d) => d.kind === "videoinput")
          .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i + 1}` }));
        setDevices(cams);
        if (cams.length && !deviceId) setDeviceId(cams[0].deviceId);
      } catch (e) {
        setError(`enumerateDevices: ${(e as Error).message}`);
      }
    })();
  }, []);

  useEffect(() => {
    if (!streaming || !videoRef.current || !canvasRef.current) return;
    const v = videoRef.current; const c = canvasRef.current;
    let raf = 0;
    const tick = () => {
      if (v.videoWidth) {
        c.width = v.videoWidth; c.height = v.videoHeight;
        c.getContext("2d")?.drawImage(v, 0, 0);
        setLiveImbalance(lrImbalance(c));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [streaming]);

  const start = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId } } : true,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStreaming(true);
      }
      const ds = await navigator.mediaDevices.enumerateDevices();
      const cams = ds
        .filter((d) => d.kind === "videoinput")
        .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i + 1}` }));
      setDevices(cams);
    } catch (e) {
      setError(`getUserMedia: ${(e as Error).message}`);
    }
  };

  const stop = () => {
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((t) => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreaming(false);
    setLiveImbalance(0);
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    const samples: number[] = [];
    const N = 30;
    for (let i = 0; i < N; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth;
      c.height = videoRef.current.videoHeight;
      c.getContext("2d")?.drawImage(videoRef.current, 0, 0);
      samples.push(lrImbalance(c));
      await new Promise((r) => setTimeout(r, 33));
    }
    const mean = samples.reduce((a, b) => a + b, 0) / samples.length;
    setStatus(`measured asymmetry ≈ ${mean.toFixed(3)} — sending to engine…`);
    try {
      await api.cameraRun(mean, reps, exercise);
      setStatus(`done. asymmetry=${mean.toFixed(3)}, reps=${reps}, exercise=${exercise}`);
      onAnalyzed();
    } catch (e) {
      setError(`camera/run: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section style={{
      background: "#16241b", borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: "4px solid #3a8443",
    }}>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
          style={{ padding: 6, background: "#22332a", color: "#dde7df",
            border: "1px solid #3a8443", borderRadius: 4 }}>
          {devices.length === 0 && <option value="">(grant permission to list cameras)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={exercise} onChange={(e) => setExercise(e.target.value)}
          style={{ padding: 6, background: "#22332a", color: "#dde7df",
            border: "1px solid #3a8443", borderRadius: 4 }}>
          <option value="squat">squat</option>
          <option value="pushup">pushup</option>
          <option value="deadlift">deadlift</option>
        </select>
        <label style={{ fontSize: 12 }}>
          reps:&nbsp;
          <input type="number" min={1} max={20} value={reps}
            onChange={(e) => setReps(parseInt(e.target.value) || 5)}
            style={{ width: 50, padding: 4, background: "#22332a",
              color: "#dde7df", border: "1px solid #3a8443", borderRadius: 4 }} />
        </label>
        {!streaming
          ? <button onClick={start} style={btnStyle}>Start camera</button>
          : <button onClick={stop} style={{ ...btnStyle, background: "#7d3a3a" }}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btnStyle, background: streaming && !running ? "#3a8443" : "#444",
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{
          width: 320, height: 240, background: "#000", borderRadius: 4,
        }} />
        <div style={{ minWidth: 220 }}>
          <div style={{ fontSize: 12, opacity: 0.7 }}>Live L/R imbalance</div>
          <div style={{ fontSize: 32, fontWeight: 600 }}>{liveImbalance.toFixed(3)}</div>
          <div style={{ height: 8, background: "#22332a", borderRadius: 3,
            overflow: "hidden", marginTop: 6 }}>
            <div style={{
              width: `${Math.min(100, liveImbalance * 100)}%`,
              height: "100%",
              background: liveImbalance > 0.5 ? "#e74c3c"
                : liveImbalance > 0.2 ? "#e6a23c" : "#27ae60",
            }} />
          </div>
          <div style={{ fontSize: 11, opacity: 0.6, marginTop: 8 }}>
            Browser-side: left vs right half-frame luminance imbalance.
            Sent to backend on Capture as <code>asymmetry_severity</code>.
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {status && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>{status}</div>}
      {error && <div style={{ marginTop: 8, fontSize: 12, color: "#ff8c8c" }}>{error}</div>}
    </section>
  );
}

const btnStyle = {
  padding: "6px 14px",
  background: "#3a8443",
  color: "white",
  border: 0,
  borderRadius: 4,
  cursor: "pointer" as const,
};
