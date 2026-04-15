import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

import RootApolloProvider from "./apollo-provider";

const geistSans = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = JetBrains_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Naql.ai — Autonomous Logistics Platform",
  description:
    "Next-generation AI-powered logistics ecosystem for Egypt. Real-time fleet tracking, intelligent dispatching, and automated pricing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <RootApolloProvider>{children}</RootApolloProvider>
      </body>
    </html>
  );
}
