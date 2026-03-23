import { Outlet } from "react-router-dom";
import { NavSidebar } from "./NavSidebar";

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <NavSidebar />
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
