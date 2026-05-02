import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };
const TERRAINS = ["flat", "hilly", "stairs", "mixed"] as const;

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

const COLOR = "#3a8443"; const BG = "#16241b"; const INSET = "#1d2a1d";

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveActivity, setLiveActivity] = useState(0);
  const [liveSun, setLiveSun] = useState(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [walkerId, setWalkerId] = useState("WEBCAM_W");
  const [terrain, setTerrain] = useState<string>("flat");
  const [pace, setPace] = useState(4.5);
  const [duration, setDuration] = useState(15);
  const [rest, setRest] = useState(15);
  const [temp, setTemp] = useState(22);
  const [hr, setHr] = useState(110);

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
          if (prevRef.current) setLiveActivity(Math.min(1, meanLumDiff(prevRef.current, cur) * 25));
          setLiveSun(Math.min(1, meanLuminance(cur) / 200));
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
    setStreaming(false); setLiveActivity(0); setLiveSun(0); prevRef.current = null;
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
    const activity = motions.length ? motions.reduce((a, b) => a + b, 0) / motions.length : 0;
    const sun = lums.length ? lums.reduce((a, b) => a + b, 0) / lums.length : 0;
    setStatus(`activity≈${activity.toFixed(2)} sun≈${sun.toFixed(2)} — sending…`);
    try {
      const r = await api.cameraRun({
        walker_id: walkerId, terrain,
        pace_kmh: pace, duration_min: duration,
        activity_intensity: activity, sun_exposure_proxy: sun,
        minutes_since_rest: rest, air_temp_c: temp, hr_bpm: hr,
      });
      setStatus(`done. fatigue=${r.fatigue_index.toFixed(2)} pace=${r.pace_advisory}`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={{ background: BG, borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: `4px solid ${COLOR}` }}>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input — day walk</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={terrain} onChange={(e) => setTerrain(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
          {TERRAINS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>walker&nbsp;
          <input value={walkerId} onChange={(e) => setWalkerId(e.target.value)}
            style={{ width: 100, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        <label style={{ fontSize: 12 }}>pace km/h&nbsp;
          <input type="number" min={0} max={20} step={0.1} value={pace}
            onChange={(e) => setPace(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        <label style={{ fontSize: 12 }}>dur min&nbsp;
          <input type="number" min={0} value={duration}
            onChange={(e) => setDuration(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        <label style={{ fontSize: 12 }}>rest&nbsp;
          <input type="number" min={0} value={rest}
            onChange={(e) => setRest(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        <label style={{ fontSize: 12 }}>temp °C&nbsp;
          <input type="number" value={temp}
            onChange={(e) => setTemp(parseFloat(e.target.value) || 0)}
            style={{ width: 50, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        <label style={{ fontSize: 12 }}>HR bpm&nbsp;
          <input type="number" min={30} max={220} value={hr}
            onChange={(e) => setHr(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4, background: INSET, color: "#dde7df",
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
          <Stat label="Live activity (motion proxy)" v={liveActivity} />
          <Stat label="Live sun exposure (luminance)" v={liveSun} />
          <div style={{ fontSize: 11, opacity: 0.6, marginTop: 8 }}>
            Camera infers <b>activity</b> + <b>sun exposure</b>. Pace, duration,
            HR, temperature need GPS/wearable/sensor → manual fields above.
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

function btn(bg: string) {
  return { padding: "6px 14px", background: bg, color: "white",
    border: 0, borderRadius: 4, cursor: "pointer" as const };
}
