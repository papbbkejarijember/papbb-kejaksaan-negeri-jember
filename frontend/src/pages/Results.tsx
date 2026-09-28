import { useQuery } from "@tanstack/react-query";
import { Award, CalendarDays, FileCheck2, Gavel, Trophy } from "lucide-react";
import { Link } from "react-router-dom";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { apiGet } from "@/lib/api";
import { formatDate, formatRupiah } from "@/lib/format";
import type { Auction } from "@/lib/types";

function maskedName(name: string | null) {
  if (!name) return "Tidak ada pemenang";
  return name.split(" ").map((part) => `${part.charAt(0)}***`).join(" ");
}

export default function Results() {
  const query = useQuery({ queryKey: ["auction-results"], queryFn: () => apiGet<Auction[]>("/auctions/public/results"), retry: false });
  const results = query.data ?? [];
  return <AppShell><div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8" data-testid="results-page">
    <section className="relative overflow-hidden rounded-2xl bg-[#0f2c59] px-6 py-10 text-white shadow-xl sm:px-10" data-testid="results-hero">
      <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full border-[30px] border-[#c59b27]/15" />
      <div className="relative max-w-3xl"><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#f8e7aa]" data-testid="results-kicker">Transparansi publik</p><h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-5xl" data-testid="results-title">Rekap hasil lelang</h1><p className="mt-4 max-w-2xl text-slate-200" data-testid="results-description">Daftar lelang yang telah ditutup beserta nilai penawaran akhir dan identitas pemenang yang disamarkan.</p></div>
    </section>
    {query.isError ? <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-8 text-center text-amber-900" data-testid="results-error">Rekap belum dapat dimuat.</div> : results.length === 0 ? <div className="mt-8 rounded-2xl border-2 border-dashed border-slate-300 p-14 text-center dark:border-slate-600" data-testid="results-empty"><FileCheck2 className="mx-auto text-slate-400" size={34} /><h2 className="mt-4 text-xl font-bold text-[#0f2c59] dark:text-white" data-testid="results-empty-title">Belum ada hasil lelang</h2><p className="mt-2 text-sm text-slate-500" data-testid="results-empty-description">Hasil akan tampil setelah petugas menutup lelang dan menetapkan pemenang.</p><Link to="/" className="mt-5 inline-flex font-bold text-[#0f2c59] dark:text-[#f8e7aa]" data-testid="results-catalog-link">Lihat katalog aktif</Link></div> : <div className="grid gap-5 py-8 md:grid-cols-2" data-testid="results-grid">{results.map((auction) => <Card key={auction.id} className="border-slate-200 dark:border-slate-700 dark:bg-slate-900" data-testid={`result-card-${auction.id}`}><CardContent className="p-6"><div className="flex items-start justify-between gap-4"><div><Badge className="bg-slate-100 text-slate-700" data-testid={`result-category-${auction.id}`}>{auction.category}</Badge><h2 className="mt-3 text-xl font-bold text-[#0f2c59] dark:text-white" data-testid={`result-title-${auction.id}`}>{auction.title}</h2></div><span className="grid h-11 w-11 place-items-center rounded-xl bg-[#fef8ea] text-[#c59b27]"><Trophy size={21} /></span></div><div className="mt-5 grid gap-3 rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-800"><div className="flex justify-between gap-3"><span className="text-slate-500">Pemenang</span><strong data-testid={`result-winner-${auction.id}`}>{maskedName(auction.winner_name)}</strong></div><div className="flex justify-between gap-3"><span className="text-slate-500">Nilai akhir</span><strong className="text-[#c59b27]" data-testid={`result-winning-bid-${auction.id}`}>{formatRupiah(auction.winning_bid)}</strong></div><div className="flex justify-between gap-3"><span className="text-slate-500">Ditutup</span><strong data-testid={`result-closed-at-${auction.id}`}>{auction.closed_at ? formatDate(auction.closed_at) : formatDate(auction.ends_at)}</strong></div></div></CardContent></Card>)}</div>}
  </div></AppShell>;
}
