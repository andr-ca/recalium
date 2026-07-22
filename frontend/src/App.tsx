import * as React from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { IngestPage } from "@/pages/IngestPage";
import { ArchivePage } from "@/pages/ArchivePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SearchPage } from "@/pages/SearchPage";
import { FactsPage } from "@/pages/FactsPage";
import { CanonicalPage } from "@/pages/CanonicalPage";
import { ReviewQueuePage } from "@/pages/ReviewQueuePage";
import { AuditPage } from "@/pages/AuditPage";
import { WizardPage } from "@/pages/WizardPage";
import { MemoryDetailPage } from "@/pages/MemoryDetailPage";
import { ExplorePage } from "@/pages/ExplorePage";
import { TagFactsPage } from "@/pages/TagFactsPage";
import { getOnboardingStatus } from "@/lib/api";

function AppInner() {
  const navigate = useNavigate();

  React.useEffect(() => {
    if (localStorage.getItem("wizard_dismissed")) return;
    getOnboardingStatus()
      .then((status) => {
        if (status.should_show_wizard) {
          navigate("/wizard");
        }
      })
      .catch(() => {}); // Non-fatal — don't block app load on API error
  }, [navigate]);

  return (
    <Routes>
      <Route path="/wizard" element={<WizardPage />} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/ingest" replace />} />
        <Route path="/ingest" element={<IngestPage />} />
        <Route path="/archive" element={<ArchivePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/explore/tags/:tagId" element={<TagFactsPage />} />
        <Route path="/facts" element={<FactsPage />} />
        <Route path="/memory/:id" element={<MemoryDetailPage />} />
        <Route path="/canonical" element={<CanonicalPage />} />
        <Route path="/review-queue" element={<ReviewQueuePage />} />
        <Route path="/audit" element={<AuditPage />} />
      </Route>
    </Routes>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  );
}
