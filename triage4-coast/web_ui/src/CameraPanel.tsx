import { useEffect, useRef, useState } from "react";
import { api } from "./api";

type DeviceOpt = { deviceId: string; label: string };

const ZONE_KINDS = ["beach", "promenade", "water", "pier"] as const;

function frameStats(canvas: HTMLCanvasElement, prev: ImageData | null): {
  motion: number; variance: number; luminance: number; current: ImageData;
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
  return { motion, variance, luminance: mean, current: cur };
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);
  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState<string>("");
  const [streaming, setStreaming] = useState(false);
  const [liveDensity, setLiveDensity] = useState<number>(0);
  const [liveSun, setLiveSun] = useState<number>(0);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [zoneKind, setZoneKind] = useState<string>("beach");
  const [zoneId, setZoneId] = useState<string>("WEBCAM_ZONE");
  const [inWater, setInWater] = useState<number>(0.0);
  const [lostChild, setLostChild] = useState<boolean>(false);
  const [fallEvent, setFallEvent] = useState<boolean>(false);
  const [stationary, setStationary] = useState<number>(0.0);
  const [flowAnom, setFlowAnom] = useState<number>(0.0);
  const [slipRisk, setSlipRisk] = useState<number>(0.0);

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
        const { motion, variance, luminance, current } = frameStats(c, prevRef.current);
        prevRef.current = current;
        const dens = Math.min(1, Math.max(motion * 25, variance / 80));
        setLiveDensity(dens);
        setLiveSun(Math.min(1, luminance / 200));
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
    setLiveDensity(0); setLiveSun(0);
    prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true); setError(null); setStatus("collecting frames…");
    const densities: number[] = []; const suns: number[] = [];
    let prev: ImageData | null = null;
    const N = 30;
    for (let i = 0; i < N; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth;
      c.height = videoRef.current.videoHeight;
      c.getContext("2d")?.drawImage(videoRef.current, 0, 0);
      const { motion, variance, luminance, current } = frameStats(c, prev);
      prev = current;
      densities.push(Math.min(1, Math.max(motion * 25, variance / 80)));
      suns.push(Math.min(1, luminance / 200));
      await new Promise((r) => setTimeout(r, 33));
    }
    const density = densities.reduce((a, b) => a + b, 0) / densities.length;
    const sun = suns.reduce((a, b) => a + b, 0) / suns.length;
    setStatus(`density≈${density.toFixed(2)} sun≈${sun.toFixed(2)} — sending…`);
    try {
      await api.cameraRun({
        zone_id: zoneId, zone_kind: zoneKind,
        density_pressure: density,
        in_water_motion: inWater,
        sun_intensity: sun,
        lost_child_flag: lostChild,
        fall_event_flag: fallEvent,
        stationary_person_signal: stationary,
        flow_anomaly_signal: flowAnom,
        slip_risk_signal: slipRisk,
      });
      setStatus(`done. zone=${zoneId} (${zoneKind}) density=${density.toFixed(2)} sun=${sun.toFixed(2)}`);
      onAnalyzed();
    } catch (e) {
      setError(`camera/run: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section style={{
      background: "var(--surface)", borderRadius: 6, padding: 16, marginBottom: 16,
      borderLeft: "4px solid var(--primary)",
    }}>
      <div style={{ background: "var(--privacy-bg)", color: "var(--privacy-text)", padding: "6px 10px",
        borderRadius: 4, fontSize: 11, marginBottom: 8, border: "1px solid var(--danger-strong)" }}>
        ⚠ <b>PUBLIC SPACE SURVEILLANCE:</b> coast cameras observe a public space.
        GDPR / local privacy law typically requires visible signage. The browser
        sends only scalar summaries — no images leave the page.
      </div>
      <h2 style={{ marginTop: 0, fontSize: 16 }}>Camera input — coast strip</h2>
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
          : <button onClick={stop} style={{ ...btnStyle, background: "var(--danger-strong)" }}>Stop</button>}
        <button onClick={captureAndRun} disabled={!streaming || running}
          style={{ ...btnStyle, background: streaming && !running ? "var(--primary)" : "var(--text-disabled)",
            cursor: streaming && !running ? "pointer" : "not-allowed" }}>
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap" }}>
        <video ref={videoRef} muted playsInline style={{
          width: 320, height: 240, background: "#000", borderRadius: 4,
        }} />
        <div style={{ minWidth: 240, display: "flex", flexDirection: "column", gap: 8 }}>
          <Stat label="Live density (motion+variance)" v={liveDensity} />
          <Stat label="Live sun intensity (luminance)" v={liveSun} />
          <SliderRow label="In-water motion (manual)" value={inWater} onChange={setInWater} />
          <SliderRow label="Stationary person signal" value={stationary} onChange={setStationary} />
          <SliderRow label="Flow anomaly signal" value={flowAnom} onChange={setFlowAnom} />
          <SliderRow label="Slip risk signal" value={slipRisk} onChange={setSlipRisk} />
          <label style={{ fontSize: 12 }}>
            <input type="checkbox" checked={lostChild}
              onChange={(e) => setLostChild(e.target.checked)} />
            &nbsp;Lost-child flag
          </label>
          <label style={{ fontSize: 12 }}>
            <input type="checkbox" checked={fallEvent}
              onChange={(e) => setFallEvent(e.target.checked)} />
            &nbsp;Fall event observed
          </label>
          <div style={{ fontSize: 11, opacity: 0.6 }}>
            Camera infers <b>density</b> + <b>sun</b>. Other signals are operator
            overrides for channels that need specialized detectors (pose, IR,
            multi-frame stationary tracking).
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {status && <div style={{ marginTop: 8, fontSize: 12, opacity: 0.85 }}>{status}</div>}
      {error && <div style={{ marginTop: 8, fontSize: 12, color: "var(--danger-text)" }}>{error}</div>}
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

const inputColors = {
  background: "var(--surface-2)",
  color: "var(--text)",
  border: "1px solid var(--primary)",
  borderRadius: 4,
};
const selectStyle = { padding: 6, ...inputColors };
const btnStyle = {
  padding: "6px 14px",
  background: "var(--primary)",
  color: "white",
  border: 0,
  borderRadius: 4,
  cursor: "pointer" as const,
};
