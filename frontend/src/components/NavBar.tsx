"use client";
import React from "react";
import Link from "next/link";
import { useAuth } from "./AuthProvider";
import LogoutButton from "./LogoutButton";

// Custom styles for nav links
const linkStyle: React.CSSProperties = {
  color: "#333",
  textDecoration: "none",
  padding: "8px 14px",
  borderRadius: "6px",
  fontWeight: 500,
  transition: "background 0.2s",
  cursor: "pointer",
};

const linkHoverStyle: React.CSSProperties = {
  background: "#eef2fb",
  color: "#123184",
};

export default function NavBar() {
  const { token } = useAuth();

  // Helper for hover styling
  function StyledLink({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) {
    const [hovered, setHovered] = React.useState(false);
    return (
      <Link
        href={href}
        style={{
          ...linkStyle,
          ...(hovered ? linkHoverStyle : {}),
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {children}
      </Link>
    );
  }

  return (
    <nav
      style={{
        display: "flex",
        gap: 16,
        alignItems: "center",
        padding: "14px 30px",
        background: "#f5f7fa",
        borderBottom: "1px solid #e4e7ed",
        boxShadow: "0 2px 6px rgba(90,110,180,0.06)",
        fontSize: "1.07rem",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      <StyledLink href="/">Home</StyledLink>
      {token && <StyledLink href="/forecasts">Forecasts</StyledLink>}
      {token && <StyledLink href="/metabase-dashboard">Dashboards</StyledLink>}
      <div style={{ marginLeft: "auto" }}>
        {!token ? (
          <StyledLink href="/login">Login</StyledLink>
        ) : (
          <LogoutButton />
        )}
      </div>
    </nav>
  );
}
