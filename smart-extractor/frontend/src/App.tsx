import { MainLayout } from "./components/layout/MainLayout";
import { Routes, Route } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { Laboratory } from "./pages/Laboratory";
import { Extractor } from "./pages/Extractor";

export function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/extractor" element={<Extractor />} />
        <Route path="/lab" element={<Laboratory />} />
      </Routes>
    </MainLayout>
  );
}

