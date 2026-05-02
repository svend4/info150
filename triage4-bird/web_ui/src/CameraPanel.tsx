import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };

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

const COLOR = "#3a8443"; const BG = "#16261c"; const INSET = "#1d2a1d";

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [livePresence, setLivePresence] = useState(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [obsToken, setObsToken] = useState("WEBCAM_OBS");
  const [stationId, setStationId] = useState("WEBCAM_STATION");
  const [pres, setPres] = useState(1.0);
  const [distress, setDistress] = useState(0);
  const [wing, setWing] = useState(0);
  const [thermal, setThermal] = useState(0);
  const [deadCount, setDeadCount] = useState(0);

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
          if (prevRef.current) setLivePresence(Math.min(1, meanLumDiff(prevRef.current, cur) * 25));
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
    setStreaming(false); setLivePresence(0); prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    let prev: ImageData | null = null; const presences: number[] = [];
    for (let i = 0; i < 30; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth; c.height = videoRef.current.videoHeight;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0);
        const cur = ctx.getImageData(0, 0, c.width, c.height);
        if (prev) presences.push(Math.min(1, meanLumDiff(prev, cur) * 25));
        prev = cur;
      }
      await new Promise((r) => setTimeout(r, 33));
    }
    const presence = presences.length ? presences.reduce((a, b) => a + b, 0) / presences.length : 0;
    setStatus(`presence≈${presence.toFixed(2)} — sending…`);
    try {
      await api.cameraRun({
        obs_token: obsToken, station_id: stationId, presence_rate: presence,
        expected_species_present_fraction: pres, distress_fraction: distress,
        wingbeat_anomaly: wing, thermal_elevation: thermal,
        dead_bird_count: deadCount,
      });
      setStatus(`done. presence=${presence.toFixed(2)}`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={{ background: BG, borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: `4px solid ${COLOR}` }}>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input (bird station)</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
          style={{ padding: 6, background: INSET, color: "#dde7df",
            border: `1px solid ${COLOR}`, borderRadius: 4 }}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>obs token&nbsp;
          <input value={obsToken} onChange={(e) => setObsToken(e.target.value)}
            style={{ width: 110, padding: 4, background: INSET, color: "#dde7df",
              border: `1px solid ${COLOR}`, borderRadius: 4 }} />
        </label>
        <label style={{ fontSize: 12 }}>station&nbsp;
          <input value={stationId} onChange={(e) => setStationId(e.target.value)}
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
          <Stat label="Live presence (motion proxy)" v={livePresence} color={COLOR} inset={INSET} />
          <Slider label="Expected species present fraction" value={pres} onChange={setPres} />
          <Slider label="Distress fraction" value={distress} onChange={setDistress} />
          <Slider label="Wingbeat anomaly" value={wing} onChange={setWing} />
          <label style={{ fontSize: 12 }}>
            Thermal elevation: {thermal.toFixed(1)} °C
            <input type="range" min={0} max={10} step={0.1} value={thermal}
              onChange={(e) => setThermal(parseFloat(e.target.value))} style={{ width: "100%" }} />
          </label>
          <label style={{ fontSize: 12 }}>
            Dead bird count: {deadCount}
            <input type="range" min={0} max={20} step={1} value={deadCount}
              onChange={(e) => setDeadCount(parseInt(e.target.value) || 0)}
              style={{ width: "100%" }} />
          </label>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Camera infers <b>presence</b>. Wingbeat / thermal / dead-count
            need specialized sensors → manual sliders.
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {status && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>{status}</div>}
      {error && <div style={{ marginTop: 8, fontSize: 12, color: "#ff8c8c" }}>{error}</div>}
    </section>
  );
}

function Stat({ label, v, color, inset }: { label: string; v: number; color: string; inset: string }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.75 }}>{label}</span><span>{v.toFixed(3)}</span>
      </div>
      <div style={{ height: 6, background: inset, borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%",
          background: v > 0.7 ? "#e74c3c" : v > 0.3 ? "#e6a23c" : color }} />
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
