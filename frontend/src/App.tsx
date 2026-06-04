import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Canvas } from "./pages/Canvas";
import { Tracker } from "./pages/Tracker";
import { Results } from "./pages/Results";
import { Placeholder } from "./pages/Placeholder";
import { Plugins } from "./pages/Plugins";
import { Templates } from "./pages/Templates";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/datasets" replace />} />
        <Route path="/datasets" element={<Dashboard />} />
        <Route path="/datasets/:id" element={<Canvas />} />
        <Route path="/datasets/:id/run/:runId" element={<Tracker />} />
        <Route path="/datasets/:id/results/:runId" element={<Results />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/plugins" element={<Plugins />} />
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
