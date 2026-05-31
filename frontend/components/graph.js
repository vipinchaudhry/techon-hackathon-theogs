"use client";
import { useEffect, useMemo, useRef, useState } from "react";

// Obsidian-style portfolio graph: small nodes that float with a light physics
// simulation (repel each other, links pull, center is anchored). Pure SVG +
// requestAnimationFrame, no dependencies.
export function PortfolioGraph({ graph, selectedId, onSelect }) {
  const W = 720;
  const H = 420;
  const cx = W / 2;
  const cy = H / 2;
  const [hover, setHover] = useState(null);
  const [, force] = useState(0); // re-render tick
  const sim = useRef({ nodes: [], links: [] });
  const dragId = useRef(null);

  // node radius: small, like obsidian. center slightly bigger.
  const maxMoney = Math.max(...graph.nodes.map((n) => n.money_committed || 1), 1);
  const radiusFor = (n) =>
    n.is_center ? 13 : 5 + 7 * Math.sqrt((n.money_committed || 1) / maxMoney);

  // (re)build simulation when the graph changes
  useEffect(() => {
    const N = graph.nodes.length;
    sim.current.nodes = graph.nodes.map((n, i) => {
      const a = (i / N) * Math.PI * 2;
      return {
        ...n,
        r: radiusFor(n),
        x: n.is_center ? cx : cx + 120 * Math.cos(a) + (i % 3) * 6,
        y: n.is_center ? cy : cy + 120 * Math.sin(a) + (i % 2) * 6,
        vx: 0,
        vy: 0,
      };
    });
    sim.current.links = graph.links;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  // physics loop
  useEffect(() => {
    let raf;
    const byId = () => Object.fromEntries(sim.current.nodes.map((n) => [n.id, n]));
    function step() {
      const nodes = sim.current.nodes;
      const map = byId();
      // repulsion between all nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          let dx = a.x - b.x, dy = a.y - b.y;
          let d2 = dx * dx + dy * dy || 0.01;
          const f = 1400 / d2;
          const d = Math.sqrt(d2);
          const ux = dx / d, uy = dy / d;
          a.vx += ux * f; a.vy += uy * f;
          b.vx -= ux * f; b.vy -= uy * f;
        }
      }
      // link spring toward an ideal length
      const REST = 86;
      for (const l of sim.current.links) {
        const a = map[l.source], b = map[l.target];
        if (!a || !b) continue;
        let dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const f = (d - REST) * 0.012;
        const ux = dx / d, uy = dy / d;
        a.vx += ux * f; a.vy += uy * f;
        b.vx -= ux * f; b.vy -= uy * f;
      }
      // gentle pull to center + integrate (center node floats too, just stronger pull)
      for (const n of nodes) {
        const pull = n.is_center ? 0.004 : 0.0015;
        n.vx += (cx - n.x) * pull;
        n.vy += (cy - n.y) * pull;
        n.vx *= 0.86; n.vy *= 0.86; // damping
        if (dragId.current !== n.id) {
          n.x += n.vx; n.y += n.vy;
        }
        // keep inside the box
        n.x = Math.max(n.r + 60, Math.min(W - n.r - 60, n.x));
        n.y = Math.max(n.r + 20, Math.min(H - n.r - 20, n.y));
      }
      force((t) => (t + 1) % 1000000);
      raf = requestAnimationFrame(step);
    }
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, []);

  const colorFor = (state) =>
    state === "center" ? "#5b8def" : state === "profit" ? "#34c759" : "#f15a4a";

  const nodes = sim.current.nodes;
  const pos = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes, hover]);

  // drag handling (in svg coords)
  const svgRef = useRef(null);
  function toSvg(e) {
    const rect = svgRef.current.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * W,
      y: ((e.clientY - rect.top) / rect.height) * H,
    };
  }
  function onMove(e) {
    if (dragId.current == null) return;
    const p = toSvg(e);
    const n = nodes.find((x) => x.id === dragId.current);
    if (n) { n.x = p.x; n.y = p.y; n.vx = 0; n.vy = 0; }
  }

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: "100%", height: "auto", display: "block", touchAction: "none" }}
      onMouseMove={onMove}
      onMouseUp={() => (dragId.current = null)}
      onMouseLeave={() => (dragId.current = null)}
    >
      {sim.current.links.map((l, i) => {
        const a = pos[l.source], b = pos[l.target];
        if (!a || !b) return null;
        const active = selectedId === l.target || hover === l.target;
        return (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke={active ? "#c9d2e3" : "#e8ebf2"} strokeWidth={active ? 1.6 : 1} />
        );
      })}

      {nodes.map((n) => {
        const color = colorFor(n.state);
        const selected = selectedId === n.id;
        const hovered = hover === n.id;
        const showLabel = n.is_center || selected || hovered;
        return (
          <g key={n.id} transform={`translate(${n.x},${n.y})`} style={{ cursor: "pointer" }}
            onMouseDown={() => (dragId.current = n.id)}
            onClick={() => onSelect && onSelect(n)}
            onMouseEnter={() => setHover(n.id)}
            onMouseLeave={() => setHover(null)}>
            {(selected || hovered) && <circle r={n.r + 5} fill={color} opacity={0.18} />}
            <circle r={n.r} fill={color}
              stroke={selected ? "#2b2f38" : "#fff"} strokeWidth={selected ? 2 : 1.5} />
            {showLabel && (
              <text y={n.r + 12} textAnchor="middle" fontSize="10.5" fill="#2b2f38"
                fontWeight={n.is_center ? 700 : 500}>
                {n.name.length > 22 ? n.name.slice(0, 21) + "…" : n.name}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
