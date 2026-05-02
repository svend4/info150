import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };
const COLOR = "#a4407c"; const BG = "#251025"; const INSET = "#2c182c";

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
  const [liveWorkload, setLiveWorkload] = useState(0);
  const [sport, set_sport] = useState<string>("soccer");
  const [athleteToken, set_athleteToken] = useState("WEBCAM_ATH");
  const [v_form, set_v_form] = useState(0.15);
  const [v_recov, set_v_recov] = useState(32);

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
            setLiveWorkload(Math.min(1, meanLumDiff(prevRef.current, cur) * 25));
            
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
    setStreaming(false); setLiveWorkload(0); prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    let prev: ImageData | null = null; const motions: number[] = [];
    for (let i = 0; i < 30; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth; c.height = videoRef.current.videoHeight;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0);
        const cur = ctx.getImageData(0, 0, c.width, c.height);
        if (prev) motions.push(Math.min(1, meanLumDiff(prev, cur) * 25));
        prev = cur;
      }
      await new Promise((r) => setTimeout(r, 33));
    }
    const workload = motions.length ? motions.reduce((a, b) => a + b, 0) / motions.length : 0;
    setStatus(`workload≈${workload.toFixed(2)} — sending…`);
    try {
      await api.cameraRun({
        athlete_token: athleteToken, sport,
        workload_intensity: workload,
        form_asymmetry: v_form, recovery_drop_bpm: v_recov,
      });
      setStatus(`done. workload=${workload.toFixed(2)}`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={{ background: BG, borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: `4px solid ${COLOR}` }}>

      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input (athlete)</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={sport} onChange={(e) => set_sport(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
            <option key="soccer" value="soccer">soccer</option>
            <option key="basketball" value="basketball">basketball</option>
            <option key="tennis" value="tennis">tennis</option>
            <option key="baseball" value="baseball">baseball</option>
            <option key="sprint" value="sprint">sprint</option>
            <option key="swim" value="swim">swim</option>
            <option key="general" value="general">general</option>
        </select>
        <label style={{ fontSize: 12 }}>athlete token&nbsp;
          <input value={athleteToken} onChange={(e) => set_athleteToken(e.target.value)}
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
          <Stat label="Live workload (motion proxy)" v={liveWorkload} />
          <Slider label="Form asymmetry" value={v_form} onChange={set_v_form} />
          <label style={{ fontSize: 12 }}>
            Recovery HR drop (bpm): {v_recov}
            <input type="range" min={0} max={200} step={1} value={v_recov}
              onChange={(e) => set_v_recov(parseInt(e.target.value) || 0)}
              style={{ width: "100%" }} />
          </label>
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
