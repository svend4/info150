# triage4 — Hardware integration guide

Phase 10 preparation. This guide describes how to wire triage4 onto
real robotic platforms (UAV / quadruped / ground sensor chain) without
inventing any new contracts. The code scaffold is already in place —
the factory skeletons in `triage4/integrations/*_bridge.py` carry the
exact SDK calls a future engineer needs to fill in.

**triage4 itself needs no hardware to run** — four in-process loopback
bridges stand in for ROS2, MAVLink, Spot, and WebSocket. This document
is only relevant when moving to real hardware.

## 0. The contract

Every bridge — loopback or real — implements `PlatformBridge` from
`triage4/integrations/platform_bridge.py`:

```python
class PlatformBridge(Protocol):
    @property
    def platform_id(self) -> str: ...
    @property
    def telemetry(self) -> PlatformTelemetry: ...
    def publish_casualty(self, node: CasualtyNode) -> None: ...
    def publish_mission_graph(self, graph: MissionGraph) -> None: ...
    def publish_handoff(self, payload: dict) -> None: ...
    def send_waypoint(self, pose: GeoPose) -> None: ...
    def close(self) -> None: ...
```

Any implementation that satisfies `isinstance(bridge, PlatformBridge)`
and passes `tests/test_bridges_contract.py` is drop-in compatible with
the rest of the stack. The four loopback bridges in the repo are the
reference implementation.

## 1. Per-platform wiring

### 1.1 ROS2 (`build_rclpy_bridge`)

**Package:** `rclpy` (Humble or newer). Needs an initialised ROS2 domain
(`ros2 daemon` running, `ROS_DOMAIN_ID` set).

**Default topics** (from `LoopbackROS2Bridge.DEFAULT_TOPICS`):

| Kind | Topic | Message type (recommended) |
|---|---|---|
| `casualty` | `/triage4/casualty` | `std_msgs/String` (JSON) |
| `mission_graph` | `/triage4/mission_graph` | `std_msgs/String` (JSON) |
| `handoff` | `/triage4/handoff` | `std_msgs/String` (JSON) |
| `waypoint` | `/triage4/waypoint` | `geometry_msgs/PoseStamped` |

**Subscriptions a real bridge should own:**

- `/odom` → `nav_msgs/Odometry` — updates `telemetry.pose`.
- `/battery_state` → `sensor_msgs/BatteryState` — updates
  `telemetry.battery_pct` (as `msg.percentage * 100`).

**Coordinate frames:** ROS2 canonical frames are `map` / `odom` / `base_link`.
`GeoPose.frame` carries the frame name; the real bridge is responsible
for converting ROS2 poses into / out of `GeoPose` before publishing.

**Acceptance test:** `tests/test_bridges_contract.py` against a real
bridge instance (skipped in CI; run manually on a dev machine with
ROS2 installed).

### 1.2 MAVLink UAV (`build_pymavlink_bridge`)

**Package:** `pymavlink` (optional extra).

**Connection string examples:**

- `udp:127.0.0.1:14550` — SITL (Ardupilot / PX4 software-in-the-loop)
- `serial:/dev/ttyACM0:57600` — USB tether
- `tcp:10.0.0.5:5760` — companion computer over LAN

**Critical coordinate-frame note:** triage4 uses
`GeoPose(x=longitude, y=latitude)`. MAVLink's `mission_item_int` uses
`(x=latitude*1e7, y=longitude*1e7)`. **Swap x / y when crossing the
boundary.** This is the single most common source of flight mishaps
in ArduPilot and PX4 custom integrations. Tag: RISK_REGISTER
**BRIDGE-003**.

**Inbound loop:**

```python
msg = conn.recv_match(type=["GLOBAL_POSITION_INT", "SYS_STATUS"],
                      blocking=True, timeout=1.0)
```

**Outbound waypoint:**

```python
conn.mav.mission_item_int_send(
    conn.target_system, conn.target_component,
    seq=0,
    frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
    command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
    current=2, autocontinue=1,
    param1=0, param2=0, param3=0, param4=0,
    x=int(pose.y * 1e7),  # latitude
    y=int(pose.x * 1e7),  # longitude
    z=pose.z,
)
```

**Safety:** never arm / disarm from triage4. The bridge only publishes
waypoints; the autopilot operator controls arming.

### 1.3 Spot / quadruped (`build_bosdyn_bridge`)

**Package:** `bosdyn-client` (optional extra).

**Connection:** static hostname (Spot default `192.168.80.3`), username
and password provisioned via the Boston Dynamics admin console. Never
commit credentials to the repo — use environment variables or a secrets
manager.

**Lease lifecycle** (critical):

1. `lease_client.take()` grabs exclusive control.
2. `LeaseKeepAlive(lease_client)` keeps it alive.
3. `keep_alive.shutdown()` + `lease_client.return_lease()` in
   `close()` — a stuck lease leaves the robot uncommandable until it
   is power-cycled.

**Gait transitions:** `LoopbackSpotBridge.VALID_GAITS` is
`("sit", "stand", "walk", "trot")`. Real bosdyn motions require
`blocking_stand(cmd)` first, then
`RobotCommandBuilder.synchro_se2_trajectory_point_command(...)`.

**Frame conversion:** use `bosdyn.client.frame_helpers` to convert
between Spot's `odom` / `vision` frames and `GeoPose`.

### 1.4 WebSocket dashboard (`build_fastapi_websocket_bridge`)

**Package:** `fastapi` (already in core deps), `uvicorn`.

**Endpoint:** the loopback bridge records payloads in an in-process
deque. A real FastAPI bridge broadcasts to every connected
`WebSocket` and replays `bridge.history` on connect.

**Security (hard requirement):**

- Terminate TLS outside the app (reverse proxy / ingress).
- Require a bearer token in the first inbound frame.
- Rate-limit per client (≤ 50 msg/s is plenty for a dashboard).
- Never send PHI — the CasualtyNode `id` must be a mission-local
  synthetic identifier, not any patient identifier.

Tag: RISK_REGISTER **SEC-002**, **DATA-005**.

## 2. Health checking (pre-dispatch gate)

Before dispatching a waypoint to any real bridge, call:

```python
from triage4.integrations import check_bridge_health, safe_to_dispatch

health = check_bridge_health(bridge)
if safe_to_dispatch(health):
    bridge.send_waypoint(target_pose)
else:
    logger.warning("refusing waypoint: %s", health.reasons)
```

`check_bridge_health` returns a `BridgeHealth` with:

- `ok: bool` — all hard checks pass (connected, pose finite, battery
  in range, telemetry fresh, platform_id matches).
- `reasons: list[str]` — human-readable reasons for every failure.
- `safe_to_dispatch(health)` is strictly narrower: also refuses
  low-battery platforms because a waypoint costs energy.

## 3. First-flight checklist

Before the first real-hardware integration test, verify:

- [ ] `tests/test_bridges_contract.py` passes against the new bridge
      (run locally — this test is gated on SDK availability).
- [ ] Platform is reachable at the declared `connection_url` /
      hostname. Ping / `ros2 topic list` / `bosdyn-client` login
      succeeds from the triage4 host.
- [ ] Coordinate frame conversion verified on a known waypoint
      (a survey point on the test field).
- [ ] `BridgeHealth.ok` is true under nominal conditions.
- [ ] `BridgeHealth.ok` becomes false when the platform is
      disconnected (pull the network cable and re-check).
- [ ] Emergency stop / kill switch on the platform is tested
      independently and works.
- [ ] `close()` releases all platform resources (ROS2 node shutdown,
      pymavlink socket close, bosdyn lease return).
- [ ] No credentials in the repo or CI logs.
- [ ] The bridge is imported under a feature flag so the default
      `pip install triage4` still boots without the SDK.

## 4. Testing without hardware

The four loopback bridges are drop-in substitutes:

```python
from triage4.integrations import (
    LoopbackROS2Bridge,
    LoopbackMAVLinkBridge,
    LoopbackSpotBridge,
    LoopbackWebSocketBridge,
)
```

Each exposes testing helpers not on the `PlatformBridge` protocol:

- `LoopbackROS2Bridge.published_on(kind)` — inspect messages per topic.
- `LoopbackROS2Bridge.inject_telemetry(...)` — emulate a ROS2
  subscription callback.
- `LoopbackMAVLinkBridge.step(dt_s)` — advance the UAV simulator.
- `LoopbackSpotBridge.step(dt_s)` / `set_gait(...)` — advance the
  quadruped simulator.
- `LoopbackWebSocketBridge.history` — all published payloads.

These are test-only affordances; real bridges do not need to
implement them.

## 5. Optional dependencies

Real-hardware backends live behind optional extras in `pyproject.toml`:

```toml
[project.optional-dependencies]
ros2  = ["rclpy"]              # normally via apt, not pip
uav   = ["pymavlink>=2.4"]
spot  = ["bosdyn-client>=3.0"]
```

`pip install triage4` installs nothing robotic by default. The
loopback path is always available, so CI runs without any SDK and
the leak-check in `tests/test_end_to_end.py` asserts that no robotics
SDK is imported at package load time.

## 6. Non-goals

- **triage4 does not drive flight-control logic.** The autopilot
  owns arm / disarm / failsafe / return-to-launch.
- **triage4 does not tele-operate the platform.** The bridge
  publishes waypoints; a human operator retains teleop override.
- **triage4 does not run on the autopilot.** Autopilots are hard
  real-time systems; triage4 is a companion-computer workload.

## 7. Open questions (for Phase 10 proper)

- Should `check_bridge_health` include a liveness probe
  (ping a subscription) rather than trusting `last_update_ts`? Maybe;
  depends on the platform. ROS2 would need an explicit
  `get_last_publish_time()` helper per topic.
- Should the bridge emit a "health changed" event the autonomy layer
  can subscribe to? Would replace the current poll pattern.
- Multi-platform orchestration: when two UAVs fly together,
  `MissionGraph.robot_assignments` maps 1:1 but the platform bridges
  do not talk to each other. Phase 10 will need a
  `MultiPlatformManager`.

Tracked in `ROADMAP.md` under Phase 10 proper.
