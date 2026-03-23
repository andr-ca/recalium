import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { IngestPage } from "@/pages/IngestPage";
import { ArchivePage } from "@/pages/ArchivePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { DisabledPage } from "@/pages/DisabledPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/ingest" replace />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/archive" element={<ArchivePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          {/* Phase 2+ routes — visible but disabled in nav */}
          <Route path="/facts" element={<DisabledPage title="Facts" phase="2" />} />
          <Route path="/canonical" element={<DisabledPage title="Canonical Memory" phase="2" />} />
          <Route path="/search" element={<DisabledPage title="Search" phase="2" />} />
          <Route path="/review-queue" element={<DisabledPage title="Review Queue" phase="2" />} />
          <Route path="/audit" element={<DisabledPage title="Audit" phase="3" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
