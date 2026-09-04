import type { Metadata } from "next";

import { SiteNav } from "@/components/SiteNav";

import "./globals.css";

export const metadata: Metadata = {
  title: "ビーグル・アトラス",
  description:
    "ダーウィン『ビーグル号航海記』(1845 年第2版)を構造化データとして読む。" +
    "独立した二つの翻刻を突き合わせ、1845 年版の索引を語 → 頁の対応表として配る。",
};

// フリート共通フッタ(koho-lens が正本)。5 項目・この並び・下部固定。
const FOOTER = {
  license: "https://github.com/twill3c/beagle-atlas/blob/main/LICENSE",
  repository: "https://github.com/twill3c/beagle-atlas",
  guide: "https://claude.ai/code/artifact/b8b0b826-2423-4b82-9113-79695ac04900",
  blueprint: "https://claude.ai/code/artifact/aa50be7a-a90e-4bf6-b8e6-279cad98e0a9",
  appMenu: "https://app-menu-amber.vercel.app/",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <SiteNav />
        {children}
        <footer className="site-footer">
          <div className="site-footer__inner">
            <a href={FOOTER.license}>MIT License</a>
            <span className="site-footer__copy">© 2026 坂田哲朗</span>
            <span className="fsep">・</span>
            <a href={FOOTER.repository}>GitHub</a>
            <span className="fsep">・</span>
            <a href={FOOTER.guide}>ビーグル・アトラスの歩き方</a>
            <span className="fsep">・</span>
            <a href={FOOTER.blueprint}>ビーグル・アトラスの設計図</a>
            <span className="fsep">・</span>
            <a href={FOOTER.appMenu}>App Menu</a>
          </div>
        </footer>
      </body>
    </html>
  );
}
