import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };
const SPECIES = ["elephant", "lion", "rhino", "giraffe", "deer", "wolf"] as const;

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
  const [species, setSpecies] = useState<string>("elephant");
  const [speciesConf, setSpeciesConf] = useState(0.85);
  const [limb, setLimb] = useState(0);
  const [thermal, setThermal] = useState(0);
  const [postural, setPostural] = useState(0);
  const [body, setBody] = useState(0.85);

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
        obs_token: obsToken, species, species_confidence: speciesConf,
        presence_rate: presence,
        limb_asymmetry: limb, thermal_hotspot: thermal,
        postural_down_fraction: postural, body_condition: body,
      });
      setStatus(`done. ${obsToken} (${species}, presence ${presence.toFixed(2)})`);
      onAnalyzed();
    } catch (e) { setError(`camera/run: ${(e as Error).message}`); }
    finally { setRunning(false); }
  };

  return (
    <section style={panelStyle}>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input (trail-cam)</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} style={selectStyle}>
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={species} onChange={(e) => setSpecies(e.target.value)} style={selectStyle}>
          {SPECIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>token&nbsp;
          <input value={obsToken} onChange={(e) => setObsToken(e.target.value)}
            style={{ width: 110, padding: 4, ...inputColors }} />
        </label>
        {!streaming
          ? <button onClick={start} style={btnStyle}>Start camera</button>
          : <button onClick={stop} style={{ ...btnStyle, background: "#7d3a3a" }}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btnStyle, background: streaming && !running ? "#5fb061" : "#444",
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{ width: 320, height: 240,
          background: "#000", borderRadius: 4 }} />
        <div style={{ minWidth: 240, display: "flex", flexDirection: "column", gap: 8 }}>
          <Stat label="Live presence (motion proxy)" v={livePresence} />
          <Slider label="Species confidence" value={speciesConf} onChange={setSpeciesConf} />
          <Slider label="Limb asymmetry" value={limb} onChange={setLimb} />
          <Slider label="Thermal hotspot" value={thermal} onChange={setThermal} />
          <Slider label="Postural down fraction" value={postural} onChange={setPostural} />
          <Slider label="Body condition" value={body} onChange={setBody} />
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Camera infers <b>presence</b>. Health channels need pose / IR sensors.
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
      <div style={{ height: 6, background: "#1d2a1d", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%",
          background: v > 0.7 ? "#e74c3c" : v > 0.3 ? "#e6a23c" : "#5fb061" }} />
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
  background: "#1a2218", borderRadius: 6, padding: 16, marginBottom: 16,
  borderLeft: "4px solid #5fb061" as string,
};
const inputColors = {
  background: "#1d2a1d", color: "#dde7df",
  border: "1px solid #5fb061", borderRadius: 4,
};
const selectStyle = { padding: 6, ...inputColors };
const btnStyle = {
  padding: "6px 14px", background: "#5fb061", color: "white",
  border: 0, borderRadius: 4, cursor: "pointer" as const,
};
