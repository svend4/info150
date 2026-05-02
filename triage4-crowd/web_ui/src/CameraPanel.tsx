import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };

const ZONE_KINDS = ["concourse", "seating", "egress", "standing"] as const;

function frameStats(canvas: HTMLCanvasElement, prev: ImageData | null): {
  motion: number; variance: number; current: ImageData;
} {
  const ctx = canvas.getContext("2d")!;
  const cur = ctx.getImageData(0, 0, canvas.width, canvas.height);
  let lumSum = 0; let lumSqSum = 0; let n = 0;
  for (let i = 0; i < cur.data.length; i += 4) {
    const lum = 0.299 * cur.data[i] + 0.587 * cur.data[i + 1] + 0.114 * cur.data[i + 2];
    lumSum += lum; lumSqSum += lum * lum; n++;
  }
  const mean = lumSum / n;
  const variance = Math.sqrt(Math.max(0, lumSqSum / n - mean * mean));
  let motion = 0;
  if (prev && prev.data.length === cur.data.length) {
    let diff = 0; let m = 0;
    for (let i = 0; i < cur.data.length; i += 4) {
      const lc = 0.299 * cur.data[i] + 0.587 * cur.data[i + 1] + 0.114 * cur.data[i + 2];
      const lp = 0.299 * prev.data[i] + 0.587 * prev.data[i + 1] + 0.114 * prev.data[i + 2];
      diff += Math.abs(lc - lp); m++;
    }
    motion = (diff / m) / 255;
  }
  return { motion, variance, current: cur };
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const [streaming, setStreaming] = useState(false);
  const [liveFlow, setLiveFlow] = useState<number>(0);
  const [liveDensity, setLiveDensity] = useState<number>(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [zoneKind, setZoneKind] = useState<string>("standing");
  const [zoneId, setZoneId] = useState<string>("WEBCAM_ZONE");
  const [pressure, setPressure] = useState<number>(0);
  const [medical, setMedical] = useState<number>(0);

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
        const { motion, variance, current } = frameStats(c, prevRef.current);
        prevRef.current = current;
        setLiveFlow(Math.min(1, motion * 25));
        setLiveDensity(Math.min(1, variance / 80));
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
        video: deviceId ? { deviceId: { exact: deviceId } } : true,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStreaming(true);
      }
      const ds = await navigator.mediaDevices.enumerateDevices();
      setDevices(ds.filter((d) => d.kind === "videoinput")
        .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i + 1}` })));
    } catch (e) {
      setError(`getUserMedia: ${(e as Error).message}`);
    }
  };

  const stop = () => {
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((t) => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreaming(false);
    setLiveFlow(0); setLiveDensity(0);
    prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    const flows: number[] = []; const densities: number[] = [];
    let prev: ImageData | null = null;
    const N = 30;
    for (let i = 0; i < N; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth;
      c.height = videoRef.current.videoHeight;
      c.getContext("2d")?.drawImage(videoRef.current, 0, 0);
      const { motion, variance, current } = frameStats(c, prev);
      prev = current;
      flows.push(Math.min(1, motion * 25));
      densities.push(Math.min(1, variance / 80));
      await new Promise((r) => setTimeout(r, 33));
    }
    const flow = flows.reduce((a, b) => a + b, 0) / flows.length;
    const density = densities.reduce((a, b) => a + b, 0) / densities.length;
    setStatus(`flow≈${flow.toFixed(2)}  density≈${density.toFixed(2)} — sending…`);
    try {
      await api.cameraRun({
        zone_id: zoneId, zone_kind: zoneKind,
        flow_compaction: flow, density_pressure: density,
        pressure_level: pressure, medical_rate: medical,
      });
      setStatus(`done. zone=${zoneId} (${zoneKind}) flow=${flow.toFixed(2)} density=${density.toFixed(2)}`);
      onAnalyzed();
    } catch (e) {
      setError(`camera/run: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section style={{
      background: "#1a1f30", borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: "4px solid #5c7cfa",
    }}>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input</h2>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)}
          style={selectStyle}>
          {devices.length === 0 && <option value="">(grant permission to list cameras)</option>}
          {devices.map((d) => <option key={d.deviceId} value={d.deviceId}>{d.label}</option>)}
        </select>
        <select value={zoneKind} onChange={(e) => setZoneKind(e.target.value)} style={selectStyle}>
          {ZONE_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
        <label style={{ fontSize: 12 }}>
          zone&nbsp;
          <input value={zoneId} onChange={(e) => setZoneId(e.target.value)}
            style={{ width: 120, padding: 4, ...inputColors }} />
        </label>
        {!streaming
          ? <button onClick={start} style={btnStyle}>Start camera</button>
          : <button onClick={stop} style={{ ...btnStyle, background: "#7d3a3a" }}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btnStyle, background: streaming && !running ? "#5c7cfa" : "#444",
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{
          width: 320, height: 240, background: "#000", borderRadius: 4,
        }} />
        <div style={{ minWidth: 220, display: "flex", flexDirection: "column", gap: 8 }}>
          <Stat label="Live flow (motion proxy)" v={liveFlow} />
          <Stat label="Live density (variance proxy)" v={liveDensity} />
          <SliderRow label="Pressure (manual)" value={pressure} onChange={setPressure} />
          <SliderRow label="Medical rate (manual)" value={medical} onChange={setMedical} />
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Camera infers <b>flow</b> + <b>density</b>. Pressure / medical-rate are
            manual sliders since they need contact / detection sensors.
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
        <span style={{ opacity: 0.75 }}>{label}</span>
        <span>{v.toFixed(3)}</span>
      </div>
      <div style={{ height: 6, background: "#262d44", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.min(100, v * 100)}%`, height: "100%",
          background: v > 0.7 ? "#e74c3c" : v > 0.3 ? "#e6a23c" : "#5c7cfa" }} />
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

const inputColors = {
  background: "#262d44",
  color: "#dde7df",
  border: "1px solid #5c7cfa",
  borderRadius: 4,
};
const selectStyle = { padding: 6, ...inputColors };
const btnStyle = {
  padding: "6px 14px",
  background: "#5c7cfa",
  color: "white",
  border: 0,
  borderRadius: 4,
  cursor: "pointer" as const,
};
