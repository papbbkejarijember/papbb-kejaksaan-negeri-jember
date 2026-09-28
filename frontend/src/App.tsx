import { Routes, Route } from "react-router-dom";
import Home from "@/pages/Home";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import Admin from "@/pages/Admin";
import AuctionDetail from "@/pages/AuctionDetail";
import Results from "@/pages/Results";
import Report from "@/pages/Report";

// One <Route> per page in src/pages; BrowserRouter already wraps this in main.tsx.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/auth" element={<Auth />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/lelang/:id" element={<AuctionDetail />} />
      <Route path="/rekap" element={<Results />} />
      <Route path="/admin/berita-acara/:id" element={<Report />} />
    </Routes>
  );
}
