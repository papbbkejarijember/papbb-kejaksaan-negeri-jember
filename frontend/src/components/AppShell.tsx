import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, LogIn, LogOut, Moon, ShieldCheck, Sun, UserRound } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { apiGet, apiPost } from "@/lib/api";
import type { User } from "@/lib/types";
import { Button } from "@/components/ui/button";

interface AppShellProps {
  children: ReactNode;
}

const BPA_LOGO = "https://customer-assets-7cd3h4nn.emergentagent.net/job_auction-live-17/artifacts/jmc80t8v_LOGO_PAPBB_JEMBER.png";

export default function AppShell({ children }: AppShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [dark, setDark] = useState(false);
  const userQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiGet<User | null>("/auth/me"),
    retry: false,
  });
  const logout = useMutation({
    mutationFn: () => apiPost<void>("/auth/logout"),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ["current-user"] });
      queryClient.removeQueries({ queryKey: ["participant-dashboard"] });
      queryClient.removeQueries({ queryKey: ["admin-dashboard"] });
      toast.success("Anda telah keluar dari sesi.");
      navigate("/auth");
    },
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  const user = userQuery.data;
  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-svh bg-[#f8fafc] text-slate-900 dark:bg-[#081426] dark:text-slate-100">
      <div className="bg-[#091c3a] px-4 py-2 text-[11px] font-medium tracking-wide text-slate-200" data-testid="government-topbar">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <span data-testid="government-topbar-left">Portal resmi Kejaksaan Negeri Jember</span>
          <span className="hidden sm:inline" data-testid="government-topbar-right">Layanan Informasi Lelang Barang Rampasan &amp; Sitaan Negara</span>
        </div>
      </div>

      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 shadow-sm backdrop-blur-md dark:border-slate-700 dark:bg-[#0d203d]/95" data-testid="site-header">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
          <Link to="/" className="group mr-auto flex min-w-[220px] items-center gap-3" data-testid="brand-home-link">
            <span className="grid h-11 w-11 place-items-center overflow-hidden rounded-xl bg-black shadow-md shadow-[#0f2c59]/20 transition-transform duration-200 group-hover:-rotate-3" data-testid="brand-mark">
              <img src={BPA_LOGO} alt="Logo BPA Kejaksaan Negeri Jember" className="h-full w-full object-cover" data-testid="header-bpa-logo" />
            </span>
            <span>
              <span className="block text-[10px] font-bold uppercase tracking-[0.18em] text-[#c59b27]" data-testid="brand-kicker">Kejaksaan Negeri</span>
              <span className="block text-sm font-extrabold tracking-tight text-[#0f2c59] dark:text-white" data-testid="brand-name">JEMBER</span>
            </span>
          </Link>

          <nav className="order-3 flex w-full items-center gap-1 overflow-x-auto border-t border-slate-100 pt-2 text-sm sm:order-2 sm:w-auto sm:border-0 sm:pt-0" aria-label="Navigasi utama" data-testid="main-navigation">
            <Link to="/" className={`rounded-lg px-3 py-2 font-semibold transition-colors ${isActive("/") ? "bg-[#eff4fb] text-[#0f2c59]" : "text-slate-600 hover:bg-slate-50 hover:text-[#0f2c59] dark:text-slate-300 dark:hover:bg-slate-800"}`} data-testid="nav-catalog-link">Katalog Lelang</Link>
            <Link to="/rekap" className={`rounded-lg px-3 py-2 font-semibold transition-colors ${isActive("/rekap") ? "bg-[#eff4fb] text-[#0f2c59]" : "text-slate-600 hover:bg-slate-50 hover:text-[#0f2c59] dark:text-slate-300 dark:hover:bg-slate-800"}`} data-testid="nav-results-link">Rekap Hasil</Link>
            <Link to="/dashboard" className={`rounded-lg px-3 py-2 font-semibold transition-colors ${isActive("/dashboard") ? "bg-[#eff4fb] text-[#0f2c59]" : "text-slate-600 hover:bg-slate-50 hover:text-[#0f2c59] dark:text-slate-300 dark:hover:bg-slate-800"}`} data-testid="nav-dashboard-link">Dashboard</Link>
            {user?.role === "admin" && <Link to="/admin" className={`rounded-lg px-3 py-2 font-semibold transition-colors ${isActive("/admin") ? "bg-[#eff4fb] text-[#0f2c59]" : "text-slate-600 hover:bg-slate-50 hover:text-[#0f2c59] dark:text-slate-300 dark:hover:bg-slate-800"}`} data-testid="nav-admin-link">Panel Petugas</Link>}
          </nav>

          <div className="flex items-center gap-2" data-testid="header-actions">
            <Button variant="ghost" size="icon" onClick={() => setDark((value) => !value)} aria-label="Ubah tema" data-testid="theme-toggle-button">
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </Button>
            {user ? (
              <div className="flex items-center gap-2">
                <span className="hidden max-w-[160px] items-center gap-1.5 truncate rounded-lg bg-[#f8fafc] px-3 py-2 text-xs font-semibold text-[#0f2c59] sm:flex dark:bg-slate-800 dark:text-slate-100" data-testid="header-user-name"><UserRound size={14} />{user.full_name}</span>
                <Button variant="outline" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending} data-testid="logout-button"><LogOut size={15} />Keluar</Button>
              </div>
            ) : (
              <Link to="/auth" className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#0f2c59] px-3 text-sm font-bold text-white shadow-sm transition-colors hover:bg-[#163b72]" data-testid="header-login-link"><LogIn size={15} />Masuk</Link>
            )}
          </div>
        </div>
      </header>

      <main>{children}</main>
      <footer className="border-t border-slate-200 bg-white dark:border-slate-700 dark:bg-[#0d203d]" data-testid="site-footer">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 py-8 text-sm text-slate-500 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <span className="flex items-center gap-2 font-semibold text-[#0f2c59] dark:text-slate-100" data-testid="footer-agency"><img src={BPA_LOGO} alt="Logo BPA" className="h-8 w-8 rounded-lg object-cover" data-testid="footer-bpa-logo" /> Kejaksaan Negeri Jember</span>
          <span className="flex flex-wrap gap-3" data-testid="footer-legal-links"><Link to="/legal#privacy" className="hover:text-[#0f2c59] dark:hover:text-white" data-testid="footer-privacy-link">Kebijakan Privasi</Link><Link to="/legal#terms" className="hover:text-[#0f2c59] dark:hover:text-white" data-testid="footer-terms-link">Syarat Layanan</Link><Link to="/legal#contact" className="hover:text-[#0f2c59] dark:hover:text-white" data-testid="footer-contact-link">Kontak</Link></span>
          <span className="flex items-center gap-1" data-testid="footer-security"><ShieldCheck size={15} />Akses terenkripsi &amp; tercatat</span>
        </div>
      </footer>
    </div>
  );
}
