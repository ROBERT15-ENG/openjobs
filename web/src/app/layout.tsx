import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Header from "@/components/Header";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "OpenJobs — Find Your Next Role",
    template: "%s — OpenJobs",
  },
  description:
    "OpenJobs — AI-powered job search for Australia. Browse remote, hybrid and on-site roles from top companies.",
};

export const viewport: Viewport = {
  themeColor: "#09090f",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body>
        <a href="#main" className="skip-link">
          Skip to main content
        </a>
        <Header />
        <main id="main">{children}</main>
        <footer className="site-footer">
          <div className="foot-logo">
            Open<span>Jobs</span>
          </div>
          © 2026 OpenJobs · AI-powered job search for Australia
        </footer>
      </body>
    </html>
  );
}
