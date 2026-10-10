import Link from "next/link";
import { Atkinson_Hyperlegible, IBM_Plex_Mono } from "next/font/google";

import { getCompetition } from "@/lib/data";
import "./globals.css";

const text = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-text",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata = {
  title: "Corner routines",
  description:
    "What a team does from a corner at the 2022 World Cup: delivery, first contact, second ball.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const competition = getCompetition();
  return (
    <html lang="en" className={`${text.variable} ${mono.variable}`}>
      <body>
        <a className="skip" href="#main">
          Skip to content
        </a>
        <header className="site-header">
          <Link href="/" className="wordmark">
            <Flag />
            Corner routines
          </Link>
          <nav aria-label="Views">
            <Link href="/">Teams</Link>
            <Link href={`/match/${competition.default_match_id}`}>Match tape</Link>
          </nav>
        </header>
        <main id="main">{children}</main>
      </body>
    </html>
  );
}

function Flag() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
      <path d="M4 20 V2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M4 3 H16 L11 8 L16 13 H4 Z" fill="var(--flag)" />
    </svg>
  );
}
