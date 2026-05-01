import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { useSystemState }    from "./hooks/useSystemState";
import { Nav }               from "./components/Nav";
import { Overview }          from "./pages/Overview";
import { TunePage }          from "./pages/TunePage";
import { CalibrationPage }   from "./pages/CalibrationPage";

function App() {
  const state = useSystemState();

  return (
    <BrowserRouter>
      <Nav state={state} />
      <Routes>
        <Route path="/"                element={<Overview state={state} />} />
        <Route path="/calibration"     element={<CalibrationPage state={state} />} />
        <Route path="/tune/toolhead"
               element={<TunePage id="toolhead" title="Toolhead Camera Tuning" />} />
        <Route path="/tune/overhead"
               element={<TunePage id="overhead" title="Overhead Camera Tuning" />} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
