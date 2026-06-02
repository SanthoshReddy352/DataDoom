import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Canvas } from "./pages/Canvas";
import { Tracker } from "./pages/Tracker";
import { Results } from "./pages/Results";
import { Placeholder } from "./pages/Placeholder";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/datasets" replace />} />
        <Route path="/datasets" element={<Dashboard />} />
        <Route path="/datasets/:id" element={<Canvas />} />
        <Route path="/datasets/:id/run/:runId" element={<Tracker />} />
        <Route path="/datasets/:id/results/:runId" element={<Results />} />
        <Route
          path="/templates"
          element={
            <Placeholder
              kicker="Collections"
              title="Templates"
              body="Domain starter specs (fraud, churn, readmission) arrive in Phase 5. The gallery route is wired and ready."
            />
          }
        />
        <Route
          path="/plugins"
          element={
            <Placeholder
              kicker="Ecosystem"
              title="Plugins"
              body="Distributions, structural functions, failure modes and exporters discovered from installed packages — Phase 5. Offline; no marketplace."
            />
          }
        />
        <Route
          path="/settings"
          element={
            <Placeholder
              kicker="Preferences"
              title="Settings"
              body="DataDoom runs in a single, carefully tuned light theme. Storage and generation defaults land alongside team mode."
            />
          }
        />
        <Route path="*" element={<Navigate to="/datasets" replace />} />
      </Routes>
    </Layout>
  );
}
