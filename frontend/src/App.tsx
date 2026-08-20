import { BrowserRouter, Route, Routes } from "react-router";
import { Library } from "./components/Library";
import { Detail } from "./components/Detail";
import { Queue } from "./components/Queue";
import { Deliverables } from "./components/Deliverables";
import { Rules } from "./components/Rules";
import { ReviewDetail } from "./components/ReviewDetail";
import { ConflictDetail } from "./components/ConflictDetail";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Library />} />
        <Route path="/documents/:id" element={<Detail />} />
        <Route path="/conflicts" element={<Queue kind="conflicts" />} />
        <Route path="/findings" element={<Queue kind="findings" />} />
        <Route path="/findings/:documentId" element={<ReviewDetail kind="finding" />} />
        <Route path="/conflicts/:documentId" element={<ConflictDetail />} />
        <Route path="/deliverables" element={<Deliverables />} />
        <Route path="/rules" element={<Rules />} />
      </Routes>
    </BrowserRouter>
  );
}
