import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };
const COLOR = "#c45f30"; const BG = "#241408"; const INSET = "#2c1c10";

function meanLumDiff(a: ImageData, b: ImageData): number {
  if (a.data.length !== b.data.length) return 0;
  let s = 0; let n = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    s += Math.abs(
      (0.299 * a.data[i] + 0.587 * a.data[i+1] + 0.114 * a.data[i+2]) -
      (0.299 * b.data[i] + 0.587 * b.data[i+1] + 0.114 * b.data[i+2])
    ); n++;
  }
  return (s / n) / 255;
}

function frameVariance(img: ImageData): number {
  let s = 0; let s2 = 0; let n = 0;
  for (let i = 0; i < img.data.length; i += 4) {
    const lum = 0.299 * img.data[i] + 0.587 * img.data[i+1] + 0.114 * img.data[i+2];
    s += lum; s2 += lum * lum; n++;
  }
  const mean = s / n;
  return Math.sqrt(Math.max(0, s2 / n - mean * mean));
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [liveActivity, setLiveActivity] = useState(0);
  const [liveComplexity, setLiveComplexity] = useState(0);
  const [profile, set_profile] = useState<string>("AMBULATORY");
  const [casualtyId, set_casualtyId] = useState("WEBCAM_CASUALTY");

  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then((ds) => {
      const cams = ds.filter((d) => d.kind === "videoinput")
        .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i+1}` }));
      setDevices(cams);
      if (cams.length && !deviceId) setDeviceId(cams[0].deviceId);
    }).catch((e) => setError(`enumerateDevices: ${(e as Error).message}`));
  }, []);

  useEffect(() => {
    if (!streaming || !videoRef.current || !canvasRef.current) return;
    const v = videoRef.current; const c = canvasRef.current;
    let raf = 0;
    const tick = () => {
      if (v.videoWidth) {
        c.width = v.videoWidth; c.height = v.videoHeight;
        const ctx = c.getContext("2d");
        if (ctx) {
          ctx.drawImage(v, 0, 0);
          const cur = ctx.getImageData(0, 0, c.width, c.height);
          if (prevRef.current) {
            setLiveActivity(Math.min(1, meanLumDiff(prevRef.current, cur) * 25));
            setLiveComplexity(Math.min(1, frameVariance(cur) / 80));
          }
          prevRef.current = cur;
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); prevRef.current = null; };
  }, [streaming]);

  const start = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId } } : true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStreaming(true);
      }
      const ds = await navigator.mediaDevices.enumerateDevices();
      setDevices(ds.filter((d) => d.kind === "videoinput")
        .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i+1}` })));
    } catch (e) { setError(`getUserMedia: ${(e as Error).message}`); }
  };

  const stop = () => {
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((t) => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreaming(false); setLiveActivity(0); prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    let prev: ImageData | null = null; const motions: number[] = [];
      const arr_Complexity: number[] = [];
    for (let i = 0; i < 30; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth; c.height = videoRef.current.videoHeight;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0);
        const cur = ctx.getImageData(0, 0, c.width, c.height);
        if (prev) motions.push(Math.min(1, meanLumDiff(prev, cur) * 25));
        arr_Complexity.push(Math.min(1, frameVariance(cur) / 80));
        prev = cur;
      }
      await new Promise((r) => setTimeout(r, 33));
    }
    const activity = motions.length ? motions.reduce((a, b) => a + b, 0) / motions.length : 0;
      const complexityAvg = arr_Complexity.length ? arr_Complexity.reduce((a,b)=>a+b,0)/arr_Complexity.length : 0;
    setStatus(`activity≈${activity.toFixed(2)} — sending…`);
    try {
      await api.cameraRun({
        casualty_id: casualtyId, profile,
        scene_activity: activity, scene_complexity: complexityAvg,
      });
      setStatus(`done. activity=${activity.toFixed(2)}`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={{ background: BG, borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: `4px solid ${COLOR}` }}>
      <div style={{ background: "#3d2438", color: "#ffe0c0", padding: "6px 10px", borderRadius: 4, fontSize: 11, marginBottom: 8 }}>⚠ STRONG PRIVACY NOTE: mass-casualty footage = PHI-equivalent. Developer-test only. Production deploys must follow incident-response data-handling law.</div>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input (mass-casualty)</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={profile} onChange={(e) => set_profile(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
            <option key="RESPIRATING" value="RESPIRATING">RESPIRATING</option>
            <option key="AMBULATORY" value="AMBULATORY">AMBULATORY</option>
            <option key="UNRESPONSIVE" value="UNRESPONSIVE">UNRESPONSIVE</option>
            <option key="DECEASED" value="DECEASED">DECEASED</option>
        </select>
        <label style={{ fontSize: 12 }}>casualty id&nbsp;
          <input value={casualtyId} onChange={(e) => set_casualtyId(e.target.value)}
            style={{ width: 110, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        {!streaming
          ? <button onClick={start} style={btn(COLOR)}>Start camera</button>
          : <button onClick={stop} style={btn("#7d3a3a")}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btn(streaming && !running ? COLOR : "#444"),
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{ width: 320, height: 240,
          background: "#000", borderRadius: 4 }} />
        <div style={{ minWidth: 240, display: "flex", flexDirection: "column", gap: 8 }}>
          <Stat label="Live scene activity (motion)" v={liveActivity} />
          <Stat label="Live scene complexity (variance)" v={liveComplexity} />
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Camera-derived signals fill the green channel(s); manual sliders fill
            channels that need other sensors.
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {status && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>{status}</div>}
      {error && <div style={{ marginTop: 8, fontSize: 12, color: "#ff8c8c" }}>{error}</div>}
    </section>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.75 }}>{label}</span><span>{v.toFixed(3)}</span>
      </div>
      <div style={{ height: 6, background: INSET, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%",
          background: v > 0.7 ? "#e74c3c" : v > 0.3 ? "#e6a23c" : COLOR }} />
      </div>
    </div>
  );
}
function Slider({ label, value, onChange }: {
  label: string; value: number; onChange: (n: number) => void;
}) {
  return (
    <label style={{ fontSize: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ opacity: 0.75 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <input type="range" min={0} max={1} step={0.01} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))} style={{ width: "100%" }} />
    </label>
  );
}
function btn(bg: string) {
  return { padding: "6px 14px", background: bg, color: "white",
    border: 0, borderRadius: 4, cursor: "pointer" as const };
}
