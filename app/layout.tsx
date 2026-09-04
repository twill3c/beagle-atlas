import type { Metadata } from "next";

import { SiteNav } from "@/components/SiteNav";

import "./globals.css";

export const metadata: Metadata = {
  title: "ビーグル・アトラス",
  description:
    "ダーウィン『ビーグル号航海記』(1845 年第2版)を構造化データとして読む。" +
    "独立した二つの翻刻を突き合わせ、1845 年版の索引を語 → 頁の対応表として配る。",
};

// フリート共通フッタ(koho-lens が正本)。
// **行き先の無い項目は出さない。** GitHub リポジトリと解説アーティファクト(歩き方 / 設計図)は
// 未作成なので、用意でき次第ここに足して 5 項目に揃える。死んだリンクを配らないための判断。
const FOOTER = {
  license: "/LICENSE.txt",
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
            <a href={FOOTER.appMenu}>App Menu</a>
          </div>
        </footer>
      </body>
    </html>
  );
}
