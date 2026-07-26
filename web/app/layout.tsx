import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("http://127.0.0.1:3000"),
  title: "Convert2MD — локальная панель управления",
  description: "Конвертация документов, модели, тарифы, бюджеты и учёт использования.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
  openGraph: {
    title: "Convert2MD",
    description: "Документы → чистый Markdown",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Convert2MD",
    description: "Документы → чистый Markdown",
    images: ["/og.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body>{children}</body></html>;
}
