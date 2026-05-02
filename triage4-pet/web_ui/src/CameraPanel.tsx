import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };
const SPECIES = ["dog", "cat", "rabbit", "bird"] as const;

function meanLumDiff(a: ImageData, b: ImageData): number {
  if (a.data.length !== b.data.length) return 0;
  let s = 0; let n = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    const la = 0.299 * a.data[i] + 0.587 * a.data[i + 1] + 0.114 * a.data[i + 2];
    const lb = 0.299 * b.data[i] + 0.587 * b.data[i + 1] + 0.114 * b.data[i + 2];
    s += Math.abs(la - lb); n++;
  }
  return (s / n) / 255;
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveActivity, setLiveActivity] = useState(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [petToken, setPetToken] = useState("WEBCAM_PET");
  const [species, setSpecies] = useState<string>("dog");
  const [ageYears, setAgeYears] = useState(5);
  const [gait, setGait] = useState(0);
  const [resp, setResp] = useState(0);
  const [card, setCard] = useState(0);
  const [pain, setPain] = useState(0);

  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then((ds) => {
      const cams = ds.filter((d) => d.kind === "videoinput")
        .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i + 1}` }));
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
            const m = meanLumDiff(prevRef.current, cur);
            setLiveActivity(Math.min(1, m * 25));
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
        .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i + 1}` })));
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
    const activity = motions.length ? motions.reduce((a, b) => a + b, 0) / motions.length : 0;
    setStatus(`activity≈${activity.toFixed(2)} — sending…`);
    try {
      const r = await api.cameraRun({
        pet_token: petToken, species, age_years: ageYears,
        activity_proxy: activity,
        gait_asymmetry: gait, respiratory_elevation: resp,
        cardiac_elevation: card, pain_behavior_count: pain,
      });
      setStatus(`done. ${petToken} → ${r.recommendation}`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={panelStyle}>
      <div style={{ background: "#3d2438", color: "#ffe0c0", padding: "6px 10px",
        borderRadius: 4, fontSize: 11, marginBottom: 8 }}>
        ⚠ Owner-uploaded pet videos may contain personal data (audio / room context).
        Treat as PII: encrypt at rest, restrict access, follow local privacy law.
      </div>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} style={selectStyle}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={species} onChange={(e) => setSpecies(e.target.value)} style={selectStyle}>
          {SPECIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>token&nbsp;
          <input value={petToken} onChange={(e) => setPetToken(e.target.value)}
            style={{ width: 110, padding: 4, ...inputColors }} />
        </label>
        <label style={{ fontSize: 12 }}>age&nbsp;
          <input type="number" min={0} max={30} step={0.5} value={ageYears}
            onChange={(e) => setAgeYears(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4, ...inputColors }} />
        </label>
        {!streaming
          ? <button onClick={start} style={btnStyle}>Start camera</button>
          : <button onClick={stop} style={{ ...btnStyle, background: "#7d3a3a" }}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btnStyle, background: streaming && !running ? "#a85099" : "#444",
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{
          width: 320, height: 240, background: "#000", borderRadius: 4 }} />
        <div style={{ minWidth: 240, display: "flex", flexDirection: "column", gap: 8 }}>
          <Stat label="Live activity (motion proxy)" v={liveActivity} />
          <Slider label="Gait asymmetry" value={gait} onChange={setGait} />
          <Slider label="Respiratory elevation" value={resp} onChange={setResp} />
          <Slider label="Cardiac elevation" value={card} onChange={setCard} />
          <label style={{ fontSize: 12 }}>
            Pain behavior count: {pain}
            <input type="range" min={0} max={10} step={1} value={pain}
              onChange={(e) => setPain(parseInt(e.target.value) || 0)}
              style={{ width: "100%" }} />
          </label>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Camera infers <b>activity</b>. Gait / breathing / cardiac / pain need
            specialized detectors → manual sliders.
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
      <div style={{ height: 6, background: "#2a223a", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%",
          background: v > 0.7 ? "#e74c3c" : v > 0.3 ? "#e6a23c" : "#a85099" }} />
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
const panelStyle = {
  background: "#1f1830", borderRadius: 6, padding: 16, marginBottom: 16,
  borderLeft: "4px solid #a85099" as string,
};
const inputColors = {
  background: "#2a223a", color: "#dde7df",
  border: "1px solid #a85099", borderRadius: 4,
};
const selectStyle = { padding: 6, ...inputColors };
const btnStyle = {
  padding: "6px 14px", background: "#a85099", color: "white",
  border: 0, borderRadius: 4, cursor: "pointer" as const,
};
