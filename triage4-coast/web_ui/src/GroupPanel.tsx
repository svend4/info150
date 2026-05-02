// Tour-group panel — registration + active-group list with checkin + alerts.
//
// One column shows a "register a new group" form; the other column
// shows current groups with their state colour, headcount progress,
// and an inline checkin row. The list polls every 10 s so an "alert"
// state appears automatically when a checkin goes overdue.

import { useEffect, useState } from "react";
import { api, type GroupState, type TourGroup } from "./api";

const STATE_COLOR: Record<GroupState, string> = {
  active: "#27ae60",
  alert: "#e74c3c",
  complete: "#5c6080",
};
const STATE_BG: Record<GroupState, string> = {
  active: "#1a3022",
  alert: "#3a1a1a",
  complete: "#22293f",
};

function fmtAge(secAgo: number): string {
  if (secAgo < 60) return `${Math.round(secAgo)}s ago`;
  if (secAgo < 3600) return `${Math.round(secAgo / 60)}m ago`;
  return `${Math.round(secAgo / 3600)}h ago`;
}

export default function GroupPanel({ zoneIds }: { zoneIds: string[] }) {
  const [groupList, setGroupList] = useState<TourGroup[]>([]);
  const [error, setError] = useState<string | null>(null);

  // registration form
  const [name, setName] = useState("");
  const [expected, setExpected] = useState(10);
  const [meetingZone, setMeetingZone] = useState<string>("");
  const [operatorId, setOperatorId] = useState("");

  // per-group checkin draft (count input)
  const [draftCount, setDraftCount] = useState<Record<string, number>>({});

  const refresh = async () => {
    try {
      const r = await api.groupsList();
      setGroupList(r.groups);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 10_000);
    return () => clearInterval(t);
  }, []);

  const register = async () => {
    if (!name.trim()) return;
    try {
      await api.groupRegister({
        name: name.trim(),
        expected_count: expected,
        meeting_zone_id: meetingZone.trim() || null,
        operator_id: operatorId.trim() || null,
      });
      setName("");
      setMeetingZone("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const checkin = async (g: TourGroup) => {
    const c = draftCount[g.group_id] ?? g.last_known_count;
    try {
      await api.groupCheckin(g.group_id, { count: c });
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const complete = async (g: TourGroup) => {
    try {
      await api.groupComplete(g.group_id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async (g: TourGroup) => {
    if (!confirm(`Remove "${g.name}"?`)) return;
    try {
      await api.groupRemove(g.group_id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const now = Date.now() / 1000;

  return (
    <div style={{
      background: "#0e1422", borderRadius: 6, padding: 12,
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
        Tour groups
      </div>
      <div style={{ display: "grid",
        gridTemplateColumns: "260px 1fr", gap: 12 }}>
        {/* Registration form */}
        <div style={{ background: "#181f33", borderRadius: 4, padding: 10 }}>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>
            register new group
          </div>
          <input placeholder="Group name (e.g. Helsinki Tours)"
            value={name} onChange={(e) => setName(e.target.value)}
            style={inputStyle} />
          <label style={{ display: "block", fontSize: 11,
            opacity: 0.75, marginTop: 6 }}>
            Expected headcount: {expected}
            <input type="range" min={1} max={50} value={expected}
              onChange={(e) => setExpected(parseInt(e.target.value) || 1)}
              style={{ width: "100%" }} />
          </label>
          <select value={meetingZone}
            onChange={(e) => setMeetingZone(e.target.value)}
            style={{ ...inputStyle, marginTop: 6 }}>
            <option value="">(no meeting zone)</option>
            {zoneIds.map((z) => <option key={z} value={z}>{z}</option>)}
          </select>
          <input placeholder="operator id (optional)"
            value={operatorId} onChange={(e) => setOperatorId(e.target.value)}
            style={{ ...inputStyle, marginTop: 6 }} />
          <button onClick={register} disabled={!name.trim()}
            style={{
              ...buttonStyle, marginTop: 8,
              background: name.trim() ? "#3a8443" : "#444",
              cursor: name.trim() ? "pointer" : "not-allowed",
            }}>
            + Register
          </button>
        </div>
        {/* Group list */}
        <div style={{
          display: "flex", flexDirection: "column", gap: 8,
          maxHeight: 360, overflowY: "auto",
        }}>
          {groupList.length === 0 && (
            <div style={{ fontSize: 11, opacity: 0.6, padding: 8 }}>
              (no groups — register one on the left)
            </div>
          )}
          {groupList.map((g) => {
            const ratio = g.expected_count > 0
              ? g.last_known_count / g.expected_count : 0;
            return (
              <div key={g.group_id} style={{
                background: STATE_BG[g.state],
                borderLeft: `4px solid ${STATE_COLOR[g.state]}`,
                borderRadius: 4, padding: 10,
              }}>
                <div style={{
                  display: "flex", justifyContent: "space-between",
                  alignItems: "baseline",
                }}>
                  <div>
                    <span style={{ fontWeight: 600 }}>{g.name}</span>
                    <span style={{
                      fontSize: 11, opacity: 0.7, marginLeft: 8,
                    }}>
                      {g.last_known_count}/{g.expected_count}
                      {g.last_known_zone_id && ` · ${g.last_known_zone_id}`}
                    </span>
                  </div>
                  <span style={{
                    padding: "2px 8px", borderRadius: 3, fontSize: 10,
                    background: STATE_COLOR[g.state], color: "#fff",
                    fontWeight: 600, textTransform: "uppercase",
                  }}>
                    {g.state}
                  </span>
                </div>
                {/* Headcount progress */}
                <div style={{
                  height: 4, background: "#22293f", borderRadius: 2,
                  marginTop: 6, overflow: "hidden",
                }}>
                  <div style={{
                    width: `${Math.min(100, ratio * 100)}%`, height: "100%",
                    background: STATE_COLOR[g.state],
                  }} />
                </div>
                <div style={{ fontSize: 10, opacity: 0.6, marginTop: 4 }}>
                  last checkin {fmtAge(now - g.last_checkin_ts_unix)}
                  {g.operator_id && ` · op ${g.operator_id}`}
                </div>
                {g.state !== "complete" && (
                  <div style={{
                    display: "flex", gap: 6, marginTop: 6,
                    alignItems: "center",
                  }}>
                    <input type="number" min={0} max={g.expected_count}
                      value={draftCount[g.group_id] ?? g.last_known_count}
                      onChange={(e) => setDraftCount({
                        ...draftCount,
                        [g.group_id]: parseInt(e.target.value) || 0,
                      })}
                      style={{ ...inputStyle, width: 60 }} />
                    <button onClick={() => checkin(g)}
                      style={{ ...buttonStyle,
                        background: "#5c7cfa", cursor: "pointer" }}>
                      Check in
                    </button>
                    <button onClick={() => complete(g)}
                      style={{ ...buttonStyle,
                        background: "#22293f", cursor: "pointer",
                        border: "1px solid #5c7cfa" }}>
                      ✓ Complete
                    </button>
                    <button onClick={() => remove(g)}
                      style={{ ...buttonStyle,
                        background: "transparent",
                        color: "#ff8c8c", cursor: "pointer",
                        border: "1px solid #7d3a3a", marginLeft: "auto" }}>
                      Remove
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {error && (
        <div style={{ marginTop: 8, fontSize: 11, color: "#ff8c8c" }}>
          {error}
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%", padding: 6, background: "#22293f",
  color: "#dde7df", border: "1px solid #5c7cfa", borderRadius: 4,
  fontFamily: "inherit", fontSize: 12, boxSizing: "border-box",
};

const buttonStyle: React.CSSProperties = {
  padding: "4px 10px", color: "#fff", border: 0,
  borderRadius: 4, fontSize: 11,
};
