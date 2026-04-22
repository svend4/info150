# Phase 10 — Stage 1: SITL (no hardware)

End-to-end path for testing the **real** platform bridges without
any physical robot. Exercises `PyMAVLinkBridge` against ArduPilot
SITL (Software-In-The-Loop) and `ROS2Bridge` against a ROS2 domain
running under Gazebo or Ignition.

Closes RISK_REGISTER **BRIDGE-001**, **BRIDGE-002**, **BRIDGE-003**
without needing real hardware. Cost: $0.

## 0. What's covered in this stage

- The real pymavlink code path in `PyMAVLinkBridge` actually sends
  / receives real MAVLink on a real UDP socket.
- The real rclpy code path in `ROS2Bridge` actually publishes /
  subscribes on a real ROS2 graph.
- The coordinate-frame swap (triage4 `(x=lon, y=lat)` ↔ MAVLink
  `(lat*1e7, lon*1e7)`) is verified against a real autopilot.
- `tests/test_bridges_contract.py` becomes runnable against a live
  backend (still passes in CI via loopback).

## 1. ArduPilot SITL

### 1.1 Install

Ubuntu (20.04+) or WSL2:

```bash
sudo apt install -y git python3-pip python3-dev \
    libxml2-dev libxslt1-dev python3-numpy python3-matplotlib
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot
cd ardupilot
Tools/environment_install/install-prereqs-Ubuntu.sh -y
. ~/.profile
./waf configure --board sitl
./waf copter
```

macOS (Homebrew):

```bash
brew install gcc python3
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot
cd ardupilot
Tools/environment_install/install-prereqs-mac.sh
./waf configure --board sitl
./waf copter
```

### 1.2 Launch

```bash
cd ~/ardupilot/ArduCopter
sim_vehicle.py --console --map
```

Wait for `APM: EKF3 IMU0 is using GPS`. At that point SITL is
publishing MAVLink on `udp:127.0.0.1:14550` (default).

### 1.3 Smoke-test against triage4

In a second terminal, from the `triage4` directory:

```bash
pip install -e '.[dev]'
pip install pymavlink
python -c "
from triage4.core.models import GeoPose
from triage4.integrations import build_pymavlink_bridge, check_bridge_health

bridge = build_pymavlink_bridge('udp:127.0.0.1:14550')
print('connected  =', bridge.telemetry.connected)
print('platform_id =', bridge.platform_id)

# Let telemetry warm up.
import time; time.sleep(2)

h = check_bridge_health(bridge)
print('health.ok   =', h.ok)
print('pose        =', bridge.telemetry.pose)
print('battery     =', bridge.telemetry.battery_pct)

# Waypoint — ArduPilot's default SITL home is near Canberra:
# lat = -35.363, lon = 149.165.
bridge.send_waypoint(GeoPose(x=149.165, y=-35.362, z=30.0))

bridge.close()
"
```

Expected output: non-zero `lat` / `lon` from the autopilot, health
`ok=True`, no exceptions. If the autopilot rejected the waypoint,
the `sim_vehicle.py` console will print an error — check the
ground-control output window.

### 1.4 Acceptance criteria

The Phase 10 Stage 1 SITL integration is considered **done** when:

- [ ] `build_pymavlink_bridge` connects to SITL on first try,
      returns in < 10 s.
- [ ] `BridgeHealth.ok` is True while SITL is running.
- [ ] `send_waypoint` with a SITL-reachable coordinate shows up
      in the MAVProxy / Mission Planner mission list.
- [ ] `tests/test_bridges_contract.py` passes against the real
      bridge (run locally; not in CI).

### 1.5 Pitfall — the lat/lon swap

ArduPilot SITL uses `MISSION_ITEM_INT` with `(x=lat*1e7,
y=lon*1e7)`. triage4 uses `GeoPose(x=longitude, y=latitude)`.

`PyMAVLinkBridge.send_waypoint` does this swap for you; it is
tested in
`tests/test_pymavlink_bridge.py::test_send_waypoint_swaps_lat_lon_correctly`.
A custom bridge that forgets the swap will fly west when you told
it to go north. Tag: RISK_REGISTER **BRIDGE-003**.

## 2. PX4 SITL (alternative)

If you prefer PX4 over ArduPilot:

```bash
git clone https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot
make px4_sitl gazebo-classic_iris
```

The same `build_pymavlink_bridge('udp:127.0.0.1:14540')` connects
(note: PX4 uses port **14540**, not 14550). Everything else —
waypoints, heartbeat, telemetry — is MAVLink-common and works
identically.

## 3. ROS2 + Gazebo / Ignition

### 3.1 Install

Ubuntu 22.04 + ROS2 Humble:

```bash
# ROS2 Humble
sudo apt install -y ros-humble-ros-base ros-humble-nav-msgs \
    ros-humble-std-msgs ros-humble-sensor-msgs
pip install rclpy  # usually already installed via apt
```

Source the workspace:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=42
```

### 3.2 Launch a minimal ROS2 graph

For a smoke test we don't need a full simulator — the triage4
bridge only needs *any* node publishing odometry + battery.
Simplest: run the turtlesim or a dummy publisher.

```bash
ros2 run turtlesim turtlesim_node &
```

Or, for a more realistic UAV simulator, install and run
`sjtu_drone` or `ardupilot_gazebo`.

### 3.3 Smoke-test against triage4

```bash
python -c "
from triage4.core.models import GeoPose
from triage4.integrations import build_rclpy_bridge, check_bridge_health

bridge = build_rclpy_bridge(platform_id='triage4_node')
print('connected =', bridge.telemetry.connected)

# Publish a triage4 event — ``ros2 topic echo /triage4/casualty``
# should show it in a second terminal.
from triage4.core.models import CasualtyNode
bridge.publish_casualty(CasualtyNode(
    id='C1', location=GeoPose(x=1.0, y=2.0),
    platform_source='ros2_node', confidence=0.9,
    status='assessed', triage_priority='immediate',
))
bridge.close()
"
```

Verification in another terminal:

```bash
ros2 topic echo /triage4/casualty
```

Expected: a single `std_msgs/String` message with JSON-encoded
casualty data.

### 3.4 Acceptance criteria

- [ ] `build_rclpy_bridge` creates a node that appears in
      `ros2 node list`.
- [ ] Every `publish_*` call surfaces on the corresponding
      `/triage4/*` topic.
- [ ] Publishing an odometry message on `/odom` updates
      `bridge.telemetry.pose`.
- [ ] Publishing a `BatteryState` on `/battery_state` updates
      `bridge.telemetry.battery_pct`.

## 4. Running the existing contract tests against the live bridge

`tests/test_bridges_contract.py` runs against Loopback by default.
To run it against the real bridges (locally, with SITL + ROS2
running):

```bash
# Monkeypatch the contract-test factories for a local debug run.
TRIAGE4_BRIDGE_BACKEND=real pytest tests/test_bridges_contract.py
```

(The env-var toggle is a convention, not yet implemented — adding
it is a small follow-up that is NOT CI-gated because it would
require SITL in CI, which is beyond the current scope.)

## 5. What is NOT covered by Stage 1

- Any real sensor input — no webcam, no thermal, no audio. The
  casualty stream is still synthetic.
- Real mobility — SITL flies a virtual aircraft, not a physical
  one.
- Multi-platform physical fleet.
- Real radio / LoRa / Bluetooth mesh. CRDT sync is exercised in
  loopback only.

Stages 2 and 3 address these.

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `BridgeUnavailable: pymavlink is not installed` | Extra missing | `pip install pymavlink` |
| `BridgeUnavailable: no MAVLink heartbeat` | SITL not running, or wrong URL | Check `sim_vehicle.py` is live; try `udp:127.0.0.1:14550` vs PX4's `14540` |
| `BridgeUnavailable: rclpy / std_msgs not importable` | ROS2 env not sourced | `source /opt/ros/humble/setup.bash` |
| Waypoint lands in wrong hemisphere | Custom bridge code missed the lat/lon swap | Use `PyMAVLinkBridge.send_waypoint`, or copy the swap block from `pymavlink_bridge.py` |
| `ros2 topic list` doesn't show `/triage4/*` | Different `ROS_DOMAIN_ID` between processes | Export the same `ROS_DOMAIN_ID` in every shell |
| `pymavlink` is installed but tests still raise `BridgeUnavailable` in CI | CI uses loopback; this is intentional | Run locally, not in CI |

## 7. Next

Once Stage 1 passes locally, proceed to
[`PHASE_10_WEBCAM.md`](PHASE_10_WEBCAM.md) — Stage 2.
