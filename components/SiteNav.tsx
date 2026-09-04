import Link from "next/link";

export function SiteNav() {
  return (
    <nav className="site-nav">
      <div className="site-nav__inner">
        <span className="site-nav__brand">
          <Link href="/">ビーグル・アトラス</Link>
        </span>
        <span className="site-nav__links">
          <Link href="/voyage/">航路と年表</Link>
          <Link href="/">底本について</Link>
          <Link href="/index-gold/">1845 年版の索引</Link>
        </span>
      </div>
    </nav>
  );
}
