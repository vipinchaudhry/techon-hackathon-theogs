"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { IconHome, IconGrid, IconScale } from "./icons";

const NAV = [
  { href: "/", label: "Portfolio", Icon: IconHome },
  { href: "/compare", label: "Compare", Icon: IconScale },
];

export function Sidebar() {
  const pathname = usePathname();
  const [health, setHealth] = useState(null);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const isActive = (href) =>
    href === "/" ? pathname === "/" || pathname.startsWith("/project") || pathname.startsWith("/scenario") : pathname === href;

  return (
    <aside className="sidebar">
      <div className="logo">
        <span className="mark">UN</span>
        <span className="name">Navigator</span>
      </div>

      <div className="side-label">Menu</div>
      {NAV.map(({ href, label, Icon }) => (
        <Link key={href} href={href} className={`nav-item ${isActive(href) ? "active" : ""}`}>
          <Icon className="ico" />
          {label}
        </Link>
      ))}

      <div className="side-label" style={{ marginTop: 22 }}>Cases</div>
      <Link href="/scenario/kodak" className="nav-item"><IconGrid className="ico" />Kodak</Link>
      <Link href="/scenario/google" className="nav-item"><IconGrid className="ico" />Google</Link>
      <Link href="/scenario/sony" className="nav-item"><IconGrid className="ico" />Sony</Link>

      <div className="side-foot">
        <div className="mode-chip">
          <span className={`mode-dot ${health && !health.llm_mock ? "" : "off"}`} />
          {health
            ? health.llm_mock
              ? "AI: offline mode"
              : "AI: on"
            : "backend offline"}
        </div>
      </div>
    </aside>
  );
}
