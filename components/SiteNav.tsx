import Link from "next/link";

export function SiteNav() {
  return (
    <nav className="site-nav">
      <div className="site-nav__inner">
        <span className="site-nav__brand">
          <Link href="/">ビーグル・アトラス</Link>
        </span>
        <span className="site-nav__links">
          <Link href="/read/">読む</Link>
          <Link href="/voyage/">航路と年表</Link>
          <Link href="/editions/">二つの版</Link>
          <Link href="/discarded/">測って、捨てた</Link>
          <Link href="/">底本について</Link>
          <Link href="/index-gold/">1845 年版の索引</Link>
        </span>
      </div>
    </nav>
  );
}
