import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BadgeCheck, CalendarDays, ChevronRight, FileSearch, Filter, Gavel, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiGet } from "@/lib/api";
import { formatDate, formatRupiah, statusLabel } from "@/lib/format";
import type { Auction, AuctionStatus } from "@/lib/types";

const BPA_BANNER = "https://customer-assets-7cd3h4nn.emergentagent.net/job_auction-live-17/artifacts/0lcc2jhj_Desain%20tanpa%20judul.png";
const BPA_LOGO = "https://customer-assets-7cd3h4nn.emergentagent.net/job_auction-live-17/artifacts/jmc80t8v_LOGO_PAPBB_JEMBER.png";

const statusStyles: Record<AuctionStatus, string> = {
  ongoing: "border-green-200 bg-green-50 text-green-800",
  upcoming: "border-blue-200 bg-blue-50 text-blue-800",
  ended: "border-slate-200 bg-slate-100 text-slate-600",
};

function AuctionCard({ auction }: { auction: Auction }) {
  return (
    <Card className="group overflow-hidden border-slate-200 bg-white shadow-sm transition-shadow duration-300 hover:border-[#c59b27]/70 hover:shadow-xl dark:border-slate-700 dark:bg-slate-900" data-testid={`auction-card-${auction.id}`}>
      <div className="relative h-40 overflow-hidden bg-[#0f2c59] text-white">{auction.image_url ? <img src={auction.image_url} alt={`Foto ${auction.title}`} className="absolute inset-0 h-full w-full object-cover" data-testid={`auction-card-image-${auction.id}`} /> : null}<div className={`absolute inset-0 ${auction.image_url ? "bg-gradient-to-t from-[#0a1d3c]/90 via-[#0f2c59]/25 to-transparent" : "bg-[#0f2c59]"}`} />
        <div className="absolute -right-6 -top-10 h-40 w-40 rounded-full border-[18px] border-[#c59b27]/20" />
        <div className="absolute -bottom-12 right-16 h-28 w-28 rounded-full bg-[#163b72]" />
        <div className="relative flex h-full flex-col justify-between">
          <div className="flex items-start justify-between gap-2">
            <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#f8e7aa]" data-testid={`auction-card-category-${auction.id}`}>{auction.category}</span>
            <Badge className={`border ${statusStyles[auction.status]}`} data-testid={`auction-status-${auction.id}`}>{statusLabel(auction.status)}</Badge>
          </div>
          <Gavel className="text-[#c59b27]" size={28} data-testid={`auction-card-icon-${auction.id}`} />
        </div>
      </div>
      <CardContent className="flex min-h-[218px] flex-col gap-4 p-5">
        <div>
          <h3 className="line-clamp-2 text-lg font-bold leading-snug text-[#0f2c59] dark:text-white" data-testid={`auction-title-${auction.id}`}>{auction.title}</h3>
          <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-slate-500" data-testid={`auction-description-${auction.id}`}>{auction.description}</p>
        </div>
        <div className="mt-auto space-y-2 text-xs text-slate-500">
          <div className="flex items-center justify-between gap-3"><span className="flex items-center gap-1.5"><CalendarDays size={14} />Mulai</span><span className="font-semibold text-slate-700 dark:text-slate-300" data-testid={`auction-start-${auction.id}`}>{formatDate(auction.starts_at)}</span></div>
          <div className="flex items-center justify-between gap-3"><span>Harga limit</span><span className="font-bold text-[#0f2c59] dark:text-[#f8e7aa]" data-testid={`auction-price-${auction.id}`}>{formatRupiah(auction.limit_price)}</span></div>
        </div>
        <Link to={`/lelang/${auction.id}`} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[#0f2c59] px-4 text-sm font-bold text-white transition-colors hover:bg-[#163b72]" data-testid={`auction-detail-link-${auction.id}`}>Lihat detail <ArrowRight size={15} /></Link>
      </CardContent>
    </Card>
  );
}

export default function Home() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const query = useQuery({
    queryKey: ["auctions", search, category, status],
    queryFn: () => apiGet<Auction[]>(`/auctions?search=${encodeURIComponent(search)}&category=${category}&status=${status}`),
    retry: false,
  });
  const auctions = query.data ?? [];
  const statusSummary = useMemo(() => ({
    ongoing: auctions.filter((auction) => auction.status === "ongoing").length,
    upcoming: auctions.filter((auction) => auction.status === "upcoming").length,
    ended: auctions.filter((auction) => auction.status === "ended").length,
  }), [auctions]);

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 pb-16 pt-8 sm:px-6 lg:px-8">
        <section className="relative overflow-hidden rounded-2xl border border-[#c59b27]/30 bg-gradient-to-br from-[#0f2c59] via-[#163b72] to-[#0a1d3c] px-6 py-10 text-white shadow-xl sm:px-10 lg:py-14" data-testid="hero-section">
          <img src={BPA_BANNER} alt="Identitas Bidang Pemulihan Aset dan Pengelolaan Barang Bukti" className="absolute inset-0 h-full w-full object-cover opacity-20 mix-blend-screen" data-testid="hero-bpa-banner" />
          <div className="absolute -right-24 -top-28 h-80 w-80 rounded-full border-[38px] border-[#c59b27]/10" />
          <div className="absolute bottom-0 right-1/4 h-24 w-24 rounded-full bg-[#c59b27]/10 blur-2xl" />
          <img src={BPA_LOGO} alt="Logo BPA Kejaksaan Negeri Jember" className="absolute right-10 top-1/2 hidden h-64 w-64 -translate-y-1/2 rounded-full object-cover opacity-95 shadow-2xl ring-1 ring-[#e5c158]/50 lg:block" data-testid="hero-bpa-logo" />
          <div className="relative max-w-3xl animate-[slide-up_500ms_ease-out]">
            <div className="mb-5 flex flex-wrap gap-2 text-[11px] font-bold uppercase tracking-[0.15em]">
              <span className="rounded-full bg-white/10 px-3 py-1.5 text-[#f8e7aa]" data-testid="hero-official-badge"><ShieldCheck size={13} className="mr-1 inline" /> Resmi &amp; Legal</span>
              <span className="rounded-full bg-white/10 px-3 py-1.5 text-slate-200" data-testid="hero-transparent-badge"><BadgeCheck size={13} className="mr-1 inline" /> Transparan</span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl lg:max-w-2xl lg:text-5xl" data-testid="hero-title">Lelang negara yang terbuka, tertib, dan dapat dipercaya.</h1>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-slate-200 sm:text-lg" data-testid="hero-description">Temukan informasi lelang barang rampasan dan sitaan negara yang dikelola Kejaksaan Negeri Jember dengan proses yang transparan untuk masyarakat.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#katalog" className="inline-flex h-11 items-center gap-2 rounded-lg bg-[#c59b27] px-5 text-sm font-extrabold text-[#0a1d3c] shadow-lg shadow-black/10 transition-colors hover:bg-[#e5c158]" data-testid="hero-catalog-button">Jelajahi katalog <ArrowRight size={16} /></a>
              <Link to="/auth" className="inline-flex h-11 items-center gap-2 rounded-lg border border-white/30 px-5 text-sm font-bold text-white transition-colors hover:bg-white/10" data-testid="hero-register-button">Daftar sebagai peserta</Link>
            </div>
          </div>
        </section>

        <section className="grid gap-4 py-8 sm:grid-cols-3" aria-label="Ringkasan lelang" data-testid="auction-summary-section">
          {[{ key: "ongoing", label: "Sedang berlangsung", value: statusSummary.ongoing }, { key: "upcoming", label: "Akan datang", value: statusSummary.upcoming }, { key: "ended", label: "Selesai", value: statusSummary.ended }].map((item) => (
            <div className="flex items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900" key={item.key} data-testid={`summary-${item.key}`}>
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#eff4fb] text-[#0f2c59] dark:bg-slate-800 dark:text-[#f8e7aa]"><Gavel size={19} /></span>
              <span><span className="block text-2xl font-extrabold text-[#0f2c59] dark:text-white" data-testid={`summary-${item.key}-value`}>{item.value}</span><span className="text-xs font-semibold text-slate-500" data-testid={`summary-${item.key}-label`}>{item.label}</span></span>
            </div>
          ))}
        </section>

        <section id="katalog" className="scroll-mt-24" data-testid="catalog-section">
          <div className="flex flex-col gap-5 border-b border-slate-200 pb-6 dark:border-slate-700 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-[#c59b27]" data-testid="catalog-kicker"><Sparkles size={14} /> Katalog publik</div>
              <h2 className="text-2xl font-bold tracking-tight text-[#0f2c59] sm:text-3xl dark:text-white" data-testid="catalog-title">Barang lelang Kejari Jember</h2>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-500" data-testid="catalog-description">Gunakan pencarian dan filter untuk menemukan objek lelang yang Anda minati.</p>
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-500" data-testid="catalog-count"><FileSearch size={17} />{query.isFetching ? "Memuat katalog…" : `${auctions.length} objek ditampilkan`}</div>
          </div>

          <div className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-[1fr_170px_170px_auto] dark:border-slate-700 dark:bg-slate-900" data-testid="catalog-filters">
            <div className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={17} /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Cari nama barang atau lokasi…" className="h-11 pl-10" aria-label="Cari lelang" data-testid="auction-search-input" /></div>
            <select value={category} onChange={(event) => setCategory(event.target.value)} className="h-11 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" aria-label="Filter kategori" data-testid="auction-category-filter"><option value="all">Semua kategori</option><option value="Kendaraan">Kendaraan</option><option value="Elektronik">Elektronik</option><option value="Properti">Properti / Tanah</option><option value="Barang Sitaan Lain">Barang sitaan lain</option></select>
            <select value={status} onChange={(event) => setStatus(event.target.value)} className="h-11 rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" aria-label="Filter status" data-testid="auction-status-filter"><option value="all">Semua status</option><option value="ongoing">Berlangsung</option><option value="upcoming">Akan datang</option><option value="ended">Selesai</option></select>
            <Button variant="outline" onClick={() => { setSearch(""); setCategory("all"); setStatus("all"); }} className="h-11 gap-2" data-testid="reset-auction-filter-button"><Filter size={16} />Reset</Button>
          </div>

          {query.isError ? <div className="my-8 rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center text-sm text-amber-900" data-testid="catalog-error-state">Katalog sedang tidak dapat dimuat. Informasi halaman tetap tersedia, silakan coba lagi.</div> : auctions.length === 0 ? (
            <div className="my-8 rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50/70 px-6 py-16 text-center dark:border-slate-600 dark:bg-slate-900/60" data-testid="auction-empty-state">
              <span className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-[#eff4fb] text-[#0f2c59] dark:bg-slate-800 dark:text-[#f8e7aa]"><Gavel size={30} /></span>
              <h3 className="mt-5 text-xl font-bold text-[#0f2c59] dark:text-white" data-testid="auction-empty-title">Belum ada lelang yang dipublikasikan</h3>
              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-500" data-testid="auction-empty-description">Panitia Kejaksaan Negeri Jember sedang menyiapkan daftar objek lelang. Silakan kembali secara berkala untuk mendapatkan informasi terbaru.</p>
              <Link to="/auth" className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-[#0f2c59] hover:text-[#c59b27] dark:text-[#f8e7aa]" data-testid="auction-empty-login-link">Masuk untuk melihat dashboard peserta <ChevronRight size={16} /></Link>
            </div>
          ) : <div className="grid gap-6 py-8 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" data-testid="auction-grid">{auctions.map((auction) => <AuctionCard key={auction.id} auction={auction} />)}</div>}
        </section>
      </div>
    </AppShell>
  );
}
