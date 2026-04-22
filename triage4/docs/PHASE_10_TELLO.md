# Phase 10 — Stage 3: DJI Tello (~$100)

End-to-end path for running triage4 on a real, flying, programmable
drone. The DJI Tello / Tello EDU is the cheapest drone with a
first-class Python SDK (`djitellopy`) and a 720p onboard camera, so
it's the practical entry point for Phase 10 proper.

Closes the last of the Phase-10-prep risks: the bridge contract
travels from "loopback-only" to "flown on real hardware" without
writing new integration code.

## 0. What's covered in this stage

- `integrations.LoopbackTelloBridge` — in-process simulator. Uses
  the Tello's real envelope (20 cm minimum move, 500 cm max move,
  ~10 min flight endurance, 80 cm takeoff altitude). Always
  available; no `djitellopy` needed.
- `integrations.TelloBridge` — real backend. Translates a triage4
  `GeoPose(x, y, z)` relative pose (in metres) into Tello-body
  `move_forward / move_back / move_right / move_left / move_up /
  move_down` commands in centimetres. Clamps below-minimum moves
  up to 20 cm (the firmware's floor); clamps above-maximum moves
  down to 500 cm.
- `integrations.build_tello_bridge` — lazy factory. Raises
  `BridgeUnavailable` if `djitellopy` is missing or the drone
  doesn't respond.
- `examples/tello_triage_demo.py` — runnable demo that flies a
  three-waypoint survey triangle, publishes casualty events, and
  uses `MultiPlatformManager` health-gating.

## 1. Hardware & install

Any Tello family drone works: **Tello (original)**, **Tello EDU**
(recommended — better stability, swappable battery, Mission Pad
support), **Ryze Tello**, **RoboMaster TT**.

```bash
pip install djitellopy
```

On the drone side:

1. Power on the Tello.
2. Join the Tello's Wi-Fi AP (SSID `TELLO-XXXXXX`) from the
   triage4 host.
3. The Tello defaults to `192.168.10.1`.

With Tello EDU you can join the drone to your *own* Wi-Fi instead
of using its AP — consult the EDU SDK docs. The bridge's `host`
argument picks up the change transparently.

## 2. Smoke test — loopback

Runs anywhere, no Tello needed:

```bash
python examples/tello_triage_demo.py
```

Expected: 3 waypoints dispatched, 3 casualties published, battery
drops visibly (each waypoint uses ~0.5% in the simulator). Exit 0.

## 3. First real flight

```bash
python examples/tello_triage_demo.py --real
```

The script tries `build_tello_bridge('192.168.10.1')`. On
`BridgeUnavailable` it silently falls back to loopback so you can't
brick a demo by forgetting to power on the drone. First-flight
recommendations:

- **Fly indoors in a clear space.** The simulator's default survey
  triangle is 2 m × 2 m — plan for 3 m × 3 m in reality.
- **Battery ≥ 50%.** The Tello firmware refuses takeoff below
  ~10%; triage4's `safe_to_dispatch` gate is stricter (refuses
  under 20%) so you have slack for the return-to-operator move.
- **Watch the physical drone**, not the triage4 log. The script
  is a *hypothesis generator* for the real flight, not a
  substitute for a human-in-the-loop pilot.

## 4. Coordinate-frame handling

### 4.1 Why Tello ≠ MAVLink

ArduPilot / PX4 bridges use GPS coordinates
(`GeoPose(x=lon, y=lat)`). The Tello has **no GPS**. Its SDK uses
a body-local frame in centimetres relative to the drone's current
heading: `(forward, right, down)`.

`TelloBridge.send_waypoint` therefore interprets `GeoPose` as a
**relative displacement in metres**:

| `GeoPose` field | Direction (body frame) | Unit conversion |
|---|---|---|
| `x` (positive) | forward / back  | metres → cm × 100 |
| `y` (positive) | right / left    | metres → cm × 100 |
| `z` (positive) | up / down       | metres → cm × 100 |

A `GeoPose(x=1.5, y=-0.8, z=0.3)` becomes
`move_forward(150)` + `move_left(80)` + `move_up(30)`.

### 4.2 Firmware clamp

Tello firmware rejects any axis command below 20 cm. The bridge
clamps up to 20 cm automatically so `GeoPose(x=0.05, ...)` doesn't
silently fail — it becomes a 20 cm move instead. The 500 cm upper
limit is enforced the same way.

## 5. Camera stream → FrameSource

`TelloBridge.frame()` returns the raw frame from
`djitellopy.Tello.get_frame_read().frame`. To feed that into the
Stage 2 perception path, wrap it in a small `FrameSource`:

```python
from triage4.integrations import build_tello_bridge

bridge = build_tello_bridge()
bridge._tello.streamon()

class _TelloFrameSource:
    def __init__(self, bridge): self._bridge = bridge
    def read(self): return self._bridge.frame()
    def close(self): self._bridge._tello.streamoff()

frame_source = _TelloFrameSource(bridge)
# Now drop this into webcam_triage_demo.py or any pipeline
# expecting a FrameSource.
```

Output is RGB (`djitellopy` pre-converts); no extra `cvtColor`
needed.

## 6. Multi-platform — Tello + webcam simultaneously

`MultiPlatformManager` accepts any mix of bridges, so a realistic
demo wiring is:

```python
from triage4.integrations import (
    MultiPlatformManager,
    LoopbackTelloBridge,
    LoopbackROS2Bridge,
)

manager = MultiPlatformManager([
    LoopbackTelloBridge(platform_id="tello_alpha"),
    LoopbackROS2Bridge(platform_id="companion"),
])
```

`send_waypoint(pose, platform_id="tello_alpha")` goes only to the
Tello; `publish_casualty(node)` broadcasts to both.

## 7. Acceptance criteria

Stage 3 is **done** when:

- [ ] `pip install djitellopy` succeeds on the dev host.
- [ ] `python examples/tello_triage_demo.py` exits 0 without a
      Tello connected.
- [ ] `python examples/tello_triage_demo.py --real` flies a 2 m
      survey triangle and lands with at least 20 % battery
      remaining.
- [ ] `tests/test_tello_bridge.py` passes — 26 tests (loopback
      kinematics + real-bridge mock + factory failure).
- [ ] `tests/test_bridges_contract.py` passes against the real
      bridge (locally, not in CI).

## 8. What is NOT covered by Stage 3

- GPS-based mission planning. The Tello has no GPS; lat/lon paths
  go through the MAVLink bridges instead.
- Multi-Tello swarms. The SDK supports it, but the bridge in this
  PR is single-drone. Add a second `build_tello_bridge` instance
  and register both in the `MultiPlatformManager` — no code
  changes needed.
- Regulatory flight-rules checking (registration, no-fly zones,
  remote ID). That belongs to the pilot, not the software.

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `BridgeUnavailable: djitellopy is not installed` | Extra missing | `pip install djitellopy` |
| `BridgeUnavailable: Tello at ... did not respond` | Not on the Tello's Wi-Fi / drone off | Join `TELLO-XXXXXX` SSID, power-cycle drone |
| Tello takes off then immediately lands | Low battery (< 10 %) | Charge to ≥ 50 % before running |
| Drone flies the wrong direction | Headless-mode / yaw bias from previous flight | Power-cycle the drone; do a fresh takeoff |
| Move command silently ignored | Displacement < 20 cm per axis | The bridge clamps this up, but double-check `GeoPose.x/y/z` values — 0 axes are skipped entirely |
| Camera frames are dark / green | `streamon()` not called before first `frame()` | Call `bridge._tello.streamon()` once at startup |
| Python script hangs on `build_tello_bridge` | Firewall blocks UDP to 192.168.10.1 | Disable / allow UDP port 8889, 8890 |

## 10. Putting the three stages together

After Stages 1 + 2 + 3 are individually done:

```
ArduPilot SITL + PyMAVLinkBridge         — Stage 1, GPS path
LoopbackWebcam  + build_ultralytics_*    — Stage 2, perception
Tello           + TelloBridge            — Stage 3, physical mobility
```

One `MultiPlatformManager` can hold all three bridges; the
perception layer reads from whichever `FrameSource` is available.
That is the minimal end-to-end demonstration that **Phase 10 real
hardware integration works** — without needing a $10,000 SAR
quadcopter.

See `docs/PHASE_10_SITL.md` (Stage 1) and
`docs/PHASE_10_WEBCAM.md` (Stage 2) for the upstream stages.
