import { NavLink } from "react-router-dom";
import {
  Upload,
  Archive,
  Lightbulb,
  BookOpen,
  Search,
  Compass,
  ClipboardList,
  FileText,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/ingest", label: "Ingest", icon: Upload, disabled: false },
  { to: "/archive", label: "Archive", icon: Archive, disabled: false },
  { to: "/facts", label: "Facts", icon: Lightbulb, disabled: false },
  { to: "/canonical", label: "Canonical", icon: BookOpen, disabled: false },
  { to: "/search", label: "Search", icon: Search, disabled: false },
  { to: "/explore", label: "Explore", icon: Compass, disabled: false },
  { to: "/review-queue", label: "Review Queue", icon: ClipboardList, disabled: false },
  { to: "/audit", label: "Audit", icon: FileText, disabled: false },
  { to: "/settings", label: "Settings", icon: Settings, disabled: false },
] as const;

export function NavSidebar() {
  return (
    <nav
      aria-label="Main navigation"
      className="flex h-full w-56 flex-col bg-[--color-sidebar-bg] text-[--color-sidebar-fg] py-4"
    >
      <div className="px-4 pb-6">
        <span className="text-lg font-bold tracking-tight">Recalium</span>
      </div>
      <ul className="flex flex-1 flex-col gap-1 px-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-[--color-sidebar-muted] text-white"
                      : "hover:bg-[--color-sidebar-muted] hover:text-white text-[--color-sidebar-fg]/80"
                  )
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
