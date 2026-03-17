import type { ReactNode } from "react";
import { useState } from "react";
import { LayoutDashboard, FileText, FlaskConical } from "lucide-react";
import { NavLink } from "react-router-dom";

type MainLayoutProps = {
  children: ReactNode;
};

type NavItem = {
  id: "dashboard" | "extractor" | "lab";
  label: string;
  icon: JSX.Element;
  to: string;
};

const NAV_ITEMS: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: <LayoutDashboard className="w-4 h-4" />,
    to: "/"
  },
  {
    id: "extractor",
    label: "Extrator",
    icon: <FileText className="w-4 h-4" />,
    to: "/extractor"
  },
  {
    id: "lab",
    label: "Laboratório",
    icon: <FlaskConical className="w-4 h-4" />,
    to: "/lab"
  }
];

export function MainLayout({ children }: MainLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 flex">
      {/* Sidebar fixa em telas md+ */}
      <aside
        className={[
          "hidden md:flex md:flex-col border-r border-slate-800 bg-slate-900/90 backdrop-blur-sm transition-all duration-200",
          collapsed ? "w-16" : "w-64",
        ].join(" ")}
      >
        <div className="h-16 flex items-center justify-between px-3 border-b border-slate-800">
          {!collapsed && (
            <span className="text-sm font-semibold tracking-tight text-slate-50">
              PJeCalc Smart Extractor
            </span>
          )}
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800 text-xs"
            aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.id}
              to={item.to}
              className={({ isActive }) =>
                [
                  "w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-slate-800 text-slate-50"
                    : "text-slate-300 hover:bg-slate-800/80 hover:text-slate-50"
                ].join(" ")
              }
            >
              <span className="inline-flex items-center justify-center rounded-md bg-slate-800/80 text-slate-200 p-1">
                {item.icon}
              </span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
        {!collapsed && (
          <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">
            Ambiente de Desenvolvimento · SaaS v3.2
          </div>
        )}
      </aside>

      {/* Conteúdo principal */}
      <div className="flex-1 flex flex-col">
        {/* Topbar móvel (md-) */}
        <header className="md:hidden h-14 flex items-center justify-between px-4 border-b border-slate-800 bg-slate-900/95 backdrop-blur">
          <span className="text-sm font-semibold text-slate-50">
            PJeCalc Smart Extractor
          </span>
          <span className="text-[11px] text-slate-400">Menu</span>
        </header>

        <main className="flex-1 px-4 py-4 md:px-6 md:py-6 bg-slate-950/95">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

