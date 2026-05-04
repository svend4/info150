import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };
const WORK_MODES = ["office", "coding", "meeting", "gaming", "streaming"] as const;

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
function meanLuminance(img: ImageData): number {
  let s = 0; let n = 0;
  for (let i = 0; i < img.data.length; i += 4) {
    s += 0.299 * img.data[i] + 0.587 * img.data[i+1] + 0.114 * img.data[i+2];
    n++;
  }
  return s / n;
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveTyping, setLiveTyping] = useState(0);
  const [liveLight, setLiveLight] = useState(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [workerId, setWorkerId] = useState("WEBCAM_W");
  const [workMode, setWorkMode] = useState<string>("office");
  const [sessionMin, setSessionMin] = useState(35);
  const [breakMin, setBreakMin] = useState(15);
  const [stretchMin, setStretchMin] = useState(60);
  const [posture, setPosture] = useState(0.85);
  const [drowsy, setDrowsy] = useState(0);
  const [distract, setDistract] = useState(0);
  const [temp, setTemp] = useState(22);
  const [hr, setHr] = useState(78);

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
          if (prevRef.current) setLiveTyping(Math.min(1, meanLumDiff(prevRef.current, cur) * 25));
          setLiveLight(Math.min(1, meanLuminance(cur) / 200));
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
    setStreaming(false); setLiveTyping(0); setLiveLight(0); prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    let prev: ImageData | null = null;
    const motions: number[] = []; const lums: number[] = [];
    for (let i = 0; i < 30; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth; c.height = videoRef.current.videoHeight;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0);
        const cur = ctx.getImageData(0, 0, c.width, c.height);
        if (prev) motions.push(Math.min(1, meanLumDiff(prev, cur) * 25));
        lums.push(Math.min(1, meanLuminance(cur) / 200));
        prev = cur;
      }
      await new Promise((r) => setTimeout(r, 33));
    }
    const typing = motions.length ? motions.reduce((a, b) => a + b, 0) / motions.length : 0;
    const ambient = lums.length ? lums.reduce((a, b) => a + b, 0) / lums.length : 0;
    setStatus(`typing≈${typing.toFixed(2)} ambient≈${ambient.toFixed(2)} — sending…`);
    try {
      const r = await api.cameraRun({
        worker_id: workerId, work_mode: workMode,
        session_min: sessionMin, minutes_since_break: breakMin,
        minutes_since_stretch: stretchMin,
        typing_intensity: typing, screen_motion_proxy: typing,
        ambient_light_proxy: ambient,
        posture_quality: posture,
        drowsiness_signal: drowsy, distraction_signal: distract,
        air_temp_c: temp, hr_bpm: hr,
      });
      setStatus(`done. fatigue=${r.fatigue_index.toFixed(2)} posture=${r.posture_advisory}`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={{ background: "var(--surface)", borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: "4px solid var(--primary)" }}>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input — desk session</h2>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} style={selectStyle}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={workMode} onChange={(e) => setWorkMode(e.target.value)} style={selectStyle}>
          {WORK_MODES.map((w) => <option key={w} value={w}>{w}</option>)}
        </select>
        <NumIn label="worker" value={workerId} onChange={setWorkerId} text width={110} />
        <NumIn label="session min" value={sessionMin} onChange={setSessionMin} width={70} />
        <NumIn label="break min" value={breakMin} onChange={setBreakMin} width={70} />
        <NumIn label="stretch min" value={stretchMin} onChange={setStretchMin} width={70} />
        <NumIn label="temp °C" value={temp} onChange={setTemp} width={60} />
        <NumIn label="HR bpm" value={hr} onChange={setHr} width={60} />
        {!streaming
          ? <button onClick={start} style={btnStyle}>Start camera</button>
          : <button onClick={stop} style={{ ...btnStyle, background: "var(--danger-strong)" }}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btnStyle,
            background: streaming && !running ? "var(--primary)" : "var(--text-disabled)",
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{ width: 320, height: 240,
          background: "#000", borderRadius: 4 }} />
        <div style={{ minWidth: 260, display: "flex", flexDirection: "column", gap: 8 }}>
          <Stat label="Live typing-rhythm (motion proxy)" v={liveTyping} />
          <Stat label="Live ambient light (luminance)" v={liveLight} />
          <SliderRow label="Posture quality (1=upright, 0=slumped)" value={posture} onChange={setPosture} />
          <SliderRow label="Drowsiness self-rating" value={drowsy} onChange={setDrowsy} />
          <SliderRow label="Distraction self-rating" value={distract} onChange={setDistract} />
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Camera infers <b>typing rhythm</b> + <b>ambient light</b>. Posture /
            drowsiness / distraction need real pose+blink detectors → manual
            self-ratings.
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {status && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>{status}</div>}
      {error && <div style={{ marginTop: 8, fontSize: 12, color: "var(--danger-text)" }}>{error}</div>}
    </section>
  );
}

function NumIn({ label, value, onChange, width = 70, text = false }: {
  label: string;
  value: number | string;
  onChange: (v: any) => void;
  width?: number;
  text?: boolean;
}) {
  return (
    <label style={{ fontSize: 12 }}>
      {label}&nbsp;
      <input type={text ? "text" : "number"} value={value as any}
        onChange={(e) => onChange(text ? e.target.value
          : (parseFloat(e.target.value) || 0))}
        style={{ width, padding: 4, background: "var(--surface-2)", color: "var(--text)",
          border: "1px solid var(--primary)", borderRadius: 4 }} />
    </label>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.75 }}>{label}</span><span>{v.toFixed(3)}</span>
      </div>
      <div style={{ height: 6, background: "var(--surface-2)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%",
          background: v > 0.7 ? "#e74c3c" : v > 0.3 ? "#e6a23c" : "var(--primary)" }} />
      </div>
    </div>
  );
}

function SliderRow({ label, value, onChange }: {
  label: string; value: number; onChange: (n: number) => void;
}) {
  return (
    <label style={{ fontSize: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <span style={{ opacity: 0.75 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <input type="range" min={0} max={1} step={0.01} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ width: "100%" }} />
    </label>
  );
}

const selectStyle: React.CSSProperties = {
  padding: 6, background: "var(--surface-2)", color: "var(--text)",
  border: "1px solid var(--primary)", borderRadius: 4,
};
const btnStyle: React.CSSProperties = {
  padding: "6px 14px", background: "var(--primary)", color: "#fff",
  border: 0, borderRadius: 4, cursor: "pointer" as const,
};
