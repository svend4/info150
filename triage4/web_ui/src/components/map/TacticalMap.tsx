// SVG tactical map — scales to any viewBox, supports mouse-pan +
// scroll-zoom, draws platforms + casualties with priority colour.

import { useEffect, useMemo, useRef, useState } from "react";

import type { MapCasualty, MapPlatform } from "../../types";
import { priorityColor } from "../../util/priority";

type Props = {
  platforms: MapPlatform[];
  casualties: MapCasualty[];
  width?: number;
  height?: number;
  onCasualtyClick?: (id: string) => void;
  selectedCasualtyId?: string | null;
};

type ViewBox = { x: number; y: number; w: number; h: number };

export default function TacticalMap({
  platforms,
  casualties,
  width = 720,
  height = 480,
  onCasualtyClick,
  selectedCasualtyId = null,
}: Props) {
  const bounds = useMemo(
    () => computeBounds(platforms, casualties, width, height),
    [platforms, casualties, width, height],
  );
  const [view, setView] = useState<ViewBox>(bounds);
  const [dragStart, setDragStart] = useState<{
    x: number;
    y: number;
    view: ViewBox;
  } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    setView(bounds);
  }, [bounds]);

  const onWheel: React.WheelEventHandler<SVGSVGElement> = (e) => {
    e.preventDefault();
    const factor = e.deltaY > 0 ? 1.15 : 1 / 1.15;
    const centerX = view.x + view.w / 2;
    const centerY = view.y + view.h / 2;
    const w = view.w * factor;
    const h = view.h * factor;
    setView({
      x: centerX - w / 2,
      y: centerY - h / 2,
      w,
      h,
    });
  };

  const onMouseDown: React.MouseEventHandler<SVGSVGElement> = (e) => {
    setDragStart({ x: e.clientX, y: e.clientY, view });
  };

  const onMouseMove: React.MouseEventHandler<SVGSVGElement> = (e) => {
    if (!dragStart || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const scaleX = dragStart.view.w / rect.width;
    const scaleY = dragStart.view.h / rect.height;
    const dx = (dragStart.x - e.clientX) * scaleX;
    const dy = (dragStart.y - e.clientY) * scaleY;
    setView({
      x: dragStart.view.x + dx,
      y: dragStart.view.y + dy,
      w: dragStart.view.w,
      h: dragStart.view.h,
    });
  };

  const onMouseUp = () => setDragStart(null);

  const onDoubleClick: React.MouseEventHandler<SVGSVGElement> = () => {
    setView(bounds);
  };

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
      style={{
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
        cursor: dragStart ? "grabbing" : "grab",
        userSelect: "none",
      }}
      onWheel={onWheel}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      onDoubleClick={onDoubleClick}
    >
      {/* grid */}
      <defs>
        <pattern
          id="grid-pattern"
          width={10}
          height={10}
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 10 0 L 0 0 0 10"
            fill="none"
            stroke="var(--border-1)"
            strokeWidth={0.3}
            opacity={0.5}
          />
        </pattern>
      </defs>
      <rect
        x={view.x - view.w}
        y={view.y - view.h}
        width={view.w * 3}
        height={view.h * 3}
        fill="url(#grid-pattern)"
      />

      {/* casualties */}
      {casualties.map((c) => {
        const selected = selectedCasualtyId === c.id;
        return (
          <g
            key={c.id}
            transform={`translate(${c.x},${c.y})`}
            onClick={() => onCasualtyClick?.(c.id)}
            style={{ cursor: "pointer" }}
          >
            <circle
              r={selected ? 3 : 2.2}
              fill={priorityColor(c.priority)}
              stroke={selected ? "var(--accent)" : "var(--bg-0)"}
              strokeWidth={selected ? 0.6 : 0.4}
            />
            <text
              x={3}
              y={1}
              fontSize={2.5}
              fill="var(--text-0)"
              style={{
                fontFamily: "var(--font-mono)",
                pointerEvents: "none",
              }}
            >
              {c.id}
            </text>
          </g>
        );
      })}

      {/* platforms */}
      {platforms.map((p) => (
        <g
          key={p.id}
          transform={`translate(${p.x},${p.y})`}
        >
          <polygon
            points="0,-3 3,2 -3,2"
            fill="var(--accent)"
            stroke="var(--bg-0)"
            strokeWidth={0.4}
          />
          <text
            x={4}
            y={1}
            fontSize={2.5}
            fill="var(--accent)"
            style={{
              fontFamily: "var(--font-mono)",
            }}
          >
            {p.id}
          </text>
        </g>
      ))}
    </svg>
  );
}

function computeBounds(
  platforms: MapPlatform[],
  casualties: MapCasualty[],
  width: number,
  height: number,
): ViewBox {
  const pts = [
    ...platforms.map((p) => ({ x: p.x, y: p.y })),
    ...casualties.map((c) => ({ x: c.x, y: c.y })),
  ];
  if (pts.length === 0) {
    return { x: 0, y: 0, w: 100, h: 75 };
  }
  const xs = pts.map((p) => p.x);
  const ys = pts.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const padX = Math.max(10, (maxX - minX) * 0.1);
  const padY = Math.max(10, (maxY - minY) * 0.1);

  let w = maxX - minX + 2 * padX;
  let h = maxY - minY + 2 * padY;
  // Keep aspect ratio of the SVG.
  const aspect = width / height;
  if (w / h > aspect) {
    h = w / aspect;
  } else {
    w = h * aspect;
  }

  return {
    x: (minX + maxX) / 2 - w / 2,
    y: (minY + maxY) / 2 - h / 2,
    w,
    h,
  };
}
