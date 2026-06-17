import type { JSX, ReactNode } from "react";

export interface NavItem {
  key: string;
  label: string;
  icon: JSX.Element;
}

export function Layout(props: {
  items: NavItem[];
  active: string;
  onSelect: (key: string) => void;
  title: string;
  eyebrow: string;
  topRight?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}): JSX.Element {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2.5v3.2M12 18.3v3.2M2.5 12h3.2M18.3 12h3.2M5.2 5.2l2.3 2.3M16.5 16.5l2.3 2.3M18.8 5.2l-2.3 2.3M7.5 16.5l-2.3 2.3" />
            </svg>
          </div>
          <div>
            <div className="brand-name">Verzahnungsanalyse</div>
            <div className="brand-sub">TUM · FZG</div>
          </div>
        </div>

        <nav className="nav">
          <div className="nav-label">Analyse</div>
          {props.items.map((it) => (
            <button
              key={it.key}
              className={`nav-item ${it.key === props.active ? "active" : ""}`}
              onClick={() => props.onSelect(it.key)}
            >
              {it.icon}
              {it.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">{props.footer}</div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">{props.eyebrow}</div>
            <h1>{props.title}</h1>
          </div>
          {props.topRight}
        </header>
        <div className="content">{props.children}</div>
      </main>
    </div>
  );
}
