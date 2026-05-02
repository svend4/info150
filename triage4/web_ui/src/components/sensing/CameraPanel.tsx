// Stationary scene-camera panel — Phase 10 integration.
//
// The browser opens a getUserMedia stream, computes per-frame
// inter-frame motion (respiration / movement proxy) and frame
// luminance variance (scene complexity / casualty count proxy),
// and posts averages to POST /camera/run together with an operator-
// chosen START priority hint. The backend builds a CasualtyNode and
// upserts it into the live graph so the rest of the dashboard
// (Casualties / Mission / Forecast / Scorecard / …) refreshes.
//
// PRIVACY: scene-camera footage is PHI-equivalent. This component
// sends only scalar summaries — no images or audio leave the
// browser.

import { useEffect, useRef, useState } from "react";
import { postCameraRun } from "../../api/endpoints";

type DeviceOpt = { deviceId: string; label: string };

const PRIORITY_OPTIONS = ["immediate", "delayed", "minimal"] as const;
type PriorityHint = (typeof PRIORITY_OPTIONS)[number];

function meanLumDiff(a: ImageData, b: ImageData): number {
  if (a.data.length !== b.data.length) return 0;
  let s = 0;
  let n = 0;
  for (let i = 0; i < a.data.length; i += 4) {
    s += Math.abs(
      0.299 * a.data[i] + 0.587 * a.data[i + 1] + 0.114 * a.data[i + 2] -
        (0.299 * b.data[i] + 0.587 * b.data[i + 1] + 0.114 * b.data[i + 2]),
    );
    n++;
  }
  return (s / n) / 255;
}

function frameVariance(img: ImageData): number {
  let s = 0;
  let s2 = 0;
  let n = 0;
  for (let i = 0; i < img.data.length; i += 4) {
    const lum = 0.299 * img.data[i] + 0.587 * img.data[i + 1] + 0.114 * img.data[i + 2];
    s += lum;
    s2 += lum * lum;
    n++;
  }
  const mean = s / n;
  return Math.sqrt(Math.max(0, s2 / n - mean * mean));
}

export default function CameraPanel({ onAnalyzed }: { onAnalyzed?: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRef = useRef<ImageData | null>(null);

  const [devices, setDevices] = useState<DeviceOpt[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [liveActivity, setLiveActivity] = useState(0);
  const [liveComplexity, setLiveComplexity] = useState(0);

  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{
    casualty_id: string;
    assigned_priority: string;
    confidence: number;
  } | null>(null);

  const [casualtyId, setCasualtyId] = useState("WEBCAM_C1");
  const [priority, setPriority] = useState<PriorityHint>("delayed");
  const [locationX, setLocationX] = useState(50);
  const [locationY, setLocationY] = useState(50);
  const [platformSource, setPlatformSource] = useState("webcam");

  useEffect(() => {
    navigator.mediaDevices
      .enumerateDevices()
      .then((ds) => {
        const cams = ds
          .filter((d) => d.kind === "videoinput")
          .map((d, i) => ({
            deviceId: d.deviceId,
            label: d.label || `Camera ${i + 1}`,
          }));
        setDevices(cams);
        if (cams.length && !deviceId) setDeviceId(cams[0].deviceId);
      })
      .catch((e) => setError(`enumerateDevices: ${(e as Error).message}`));
  }, []);

  useEffect(() => {
    if (!streaming || !videoRef.current || !canvasRef.current) return;
    const v = videoRef.current;
    const c = canvasRef.current;
    let raf = 0;
    const tick = () => {
      if (v.videoWidth) {
        c.width = v.videoWidth;
        c.height = v.videoHeight;
        const ctx = c.getContext("2d");
        if (ctx) {
          ctx.drawImage(v, 0, 0);
          const cur = ctx.getImageData(0, 0, c.width, c.height);
          if (prevRef.current) {
            setLiveActivity(Math.min(1, meanLumDiff(prevRef.current, cur) * 25));
          }
          setLiveComplexity(Math.min(1, frameVariance(cur) / 80));
          prevRef.current = cur;
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      prevRef.current = null;
    };
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
      setDevices(
        ds
          .filter((d) => d.kind === "videoinput")
          .map((d, i) => ({
            deviceId: d.deviceId,
            label: d.label || `Camera ${i + 1}`,
          })),
      );
    } catch (e) {
      setError(`getUserMedia: ${(e as Error).message}`);
    }
  };

  const stop = () => {
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach((t) => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreaming(false);
    setLiveActivity(0);
    setLiveComplexity(0);
    prevRef.current = null;
  };

  const captureAndRun = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    setRunning(true);
    setError(null);
    setStatus("collecting frames…");
    let prev: ImageData | null = null;
    const motions: number[] = [];
    const variances: number[] = [];
    for (let i = 0; i < 30; i++) {
      const c = canvasRef.current;
      c.width = videoRef.current.videoWidth;
      c.height = videoRef.current.videoHeight;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.drawImage(videoRef.current, 0, 0);
        const cur = ctx.getImageData(0, 0, c.width, c.height);
        if (prev) motions.push(Math.min(1, meanLumDiff(prev, cur) * 25));
        variances.push(Math.min(1, frameVariance(cur) / 80));
        prev = cur;
      }
      await new Promise((r) => setTimeout(r, 33));
    }
    const activity =
      motions.length ? motions.reduce((a, b) => a + b, 0) / motions.length : 0;
    const complexity =
      variances.length ? variances.reduce((a, b) => a + b, 0) / variances.length : 0;
    setStatus(
      `activity≈${activity.toFixed(2)} complexity≈${complexity.toFixed(2)} — sending…`,
    );
    try {
      const result = await postCameraRun({
        casualty_id: casualtyId,
        priority_hint: priority,
        location_x: locationX,
        location_y: locationY,
        scene_activity: activity,
        scene_complexity: complexity,
        platform_source: platformSource,
      });
      setLastResult(result);
      setStatus(
        `done. ${result.casualty_id} → ${result.assigned_priority} (conf ${result.confidence})`,
      );
      onAnalyzed?.();
    } catch (e) {
      setError(`camera/run: ${(e as Error).message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section
      style={{
        padding: 16,
        background: "var(--bg-1)",
        border: "1px solid var(--border-2)",
        borderLeft: "4px solid var(--accent)",
        borderRadius: "var(--r2)",
        marginBottom: 16,
      }}
    >
      <div
        style={{
          background: "color-mix(in srgb, var(--err) 25%, var(--bg-1))",
          color: "var(--text-0)",
          padding: "6px 10px",
          borderRadius: "var(--r1)",
          fontSize: 11,
          marginBottom: 10,
          border: "1px solid var(--err)",
        }}
      >
        ⚠ <b>STRONG PRIVACY:</b> scene-camera footage is PHI-equivalent.
        This panel sends only scalar summaries (motion + variance). No
        images / audio leave the browser. Production deploys must follow
        incident-response data-handling law.
      </div>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 12,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 16 }}>Camera input — scene triage</h2>
        <div style={{ fontSize: 11, color: "var(--text-2)" }}>
          motion → respiration proxy · variance → scene complexity proxy
        </div>
      </header>

      <div
        style={{
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <select
          value={deviceId}
          onChange={(e) => setDeviceId(e.target.value)}
          style={{ padding: 6 }}
        >
          {devices.length === 0 && <option value="">(grant permission)</option>}
          {devices.map((d) => (
            <option key={d.deviceId} value={d.deviceId}>
              {d.label}
            </option>
          ))}
        </select>
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as PriorityHint)}
          style={{ padding: 6 }}
        >
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <label style={{ fontSize: 12 }}>
          casualty&nbsp;
          <input
            value={casualtyId}
            onChange={(e) => setCasualtyId(e.target.value)}
            style={{ width: 110, padding: 4 }}
          />
        </label>
        <label style={{ fontSize: 12 }}>
          x&nbsp;
          <input
            type="number"
            value={locationX}
            onChange={(e) => setLocationX(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4 }}
          />
        </label>
        <label style={{ fontSize: 12 }}>
          y&nbsp;
          <input
            type="number"
            value={locationY}
            onChange={(e) => setLocationY(parseFloat(e.target.value) || 0)}
            style={{ width: 60, padding: 4 }}
          />
        </label>
        <label style={{ fontSize: 12 }}>
          platform&nbsp;
          <input
            value={platformSource}
            onChange={(e) => setPlatformSource(e.target.value)}
            style={{ width: 100, padding: 4 }}
          />
        </label>
        {!streaming ? (
          <button onClick={start}>Start camera</button>
        ) : (
          <button onClick={stop}>Stop</button>
        )}
        <button
          onClick={captureAndRun}
          disabled={!streaming || running}
          style={{
            background: streaming && !running ? "var(--accent)" : undefined,
            color: streaming && !running ? "var(--bg-0)" : undefined,
          }}
        >
          {running ? "Running…" : "Capture & analyze"}
        </button>
      </div>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <video
          ref={videoRef}
          muted
          playsInline
          style={{
            width: 320,
            height: 240,
            background: "#000",
            borderRadius: "var(--r1)",
          }}
        />
        <div
          style={{
            minWidth: 240,
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <Stat label="Live activity (motion proxy)" v={liveActivity} />
          <Stat label="Live complexity (variance proxy)" v={liveComplexity} />
          <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: 6 }}>
            Camera infers <b>activity</b> + <b>complexity</b>. The selected
            START priority hint chooses the canned signature profile (breathing /
            bleeding / perfusion). The triage engine assigns the final priority
            after running the signature through{" "}
            <code>RapidTriageEngine.infer_priority</code>.
          </div>
          {lastResult && (
            <div
              style={{
                marginTop: 6,
                padding: 8,
                border: "1px solid var(--border-2)",
                borderRadius: "var(--r1)",
                fontSize: 12,
              }}
            >
              <div>
                <span style={{ color: "var(--text-2)" }}>last:</span>{" "}
                <code>{lastResult.casualty_id}</code> →{" "}
                <b style={{ color: "var(--accent)" }}>
                  {lastResult.assigned_priority}
                </b>{" "}
                <span style={{ color: "var(--text-2)" }}>
                  (conf {lastResult.confidence})
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
      <canvas ref={canvasRef} style={{ display: "none" }} />
      {status && (
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-1)" }}>
          {status}
        </div>
      )}
      {error && (
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--err)" }}>
          {error}
        </div>
      )}
    </section>
  );
}

function Stat({ label, v }: { label: string; v: number }) {
  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
        }}
      >
        <span style={{ color: "var(--text-2)" }}>{label}</span>
        <span style={{ fontFamily: "var(--font-mono)" }}>{v.toFixed(3)}</span>
      </div>
      <div
        style={{
          height: 6,
          background: "var(--bg-0)",
          border: "1px solid var(--border-1)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(100, v * 100)}%`,
            height: "100%",
            background:
              v > 0.7 ? "var(--err)" : v > 0.3 ? "var(--warn)" : "var(--accent)",
          }}
        />
      </div>
    </div>
  );
}
