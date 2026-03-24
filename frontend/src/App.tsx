import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { IngestPage } from "@/pages/IngestPage";
import { ArchivePage } from "@/pages/ArchivePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SearchPage } from "@/pages/SearchPage";
import { FactsPage } from "@/pages/FactsPage";
import { CanonicalPage } from "@/pages/CanonicalPage";
import { ReviewQueuePage } from "@/pages/ReviewQueuePage";
import { AuditPage } from "@/pages/AuditPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/ingest" replace />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/archive" element={<ArchivePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/facts" element={<FactsPage />} />
          <Route path="/canonical" element={<CanonicalPage />} />
          <Route path="/review-queue" element={<ReviewQueuePage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
