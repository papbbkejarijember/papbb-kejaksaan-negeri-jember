import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Clock3, Gavel, IdCard, MapPin, ShieldCheck, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import { formatDate, formatRupiah, statusLabel } from "@/lib/format";
import type { AuctionDetail as AuctionDetailData, Bid, User } from "@/lib/types";

function errorMessage(error: unknown) {
  if (error instanceof ApiError && typeof error.body === "object" && error.body && "detail" in error.body) return String(error.body.detail);
  return "Penawaran belum dapat dikirim.";
}

export default function AuctionDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const userQuery = useQuery({ queryKey: ["current-user"], queryFn: () => apiGet<User | null>("/auth/me"), retry: false });
  const auctionQuery = useQuery({ queryKey: ["auction", id], queryFn: () => apiGet<AuctionDetailData>(`/auctions/${id}`), enabled: Boolean(id), retry: false });
  const [amount, setAmount] = useState("");
  const [remaining, setRemaining] = useState(0);
  const bidMutation = useMutation({ mutationFn: () => apiPost<Bid>(`/auctions/${id}/bids`, { amount: Number(amount) }), onSuccess: async (bid) => { await queryClient.invalidateQueries({ queryKey: ["auction", id] }); await queryClient.invalidateQueries({ queryKey: ["participant-dashboard"] }); toast.success(`Penawaran ${formatRupiah(bid.amount)} berhasil dikirim.`); setAmount(""); } });
  const auction = auctionQuery.data;

  useEffect(() => {
    if (!auction) return;
    const tick = () => setRemaining(Math.max(0, new Date(auction.ends_at).getTime() - Date.now()));
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [auction]);

  const minimum = auction ? (auction.highest_bid ?? auction.limit_price) + (auction.highest_bid === null ? 0 : auction.increment) : 0;
  const countdown = useMemo(() => {
    const totalSeconds = Math.floor(remaining / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return days > 0 ? `${days}h ${hours}j ${minutes}m` : `${String(hours).padStart(2, "0")}j ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}d`;
  }, [remaining]);
  const submit = (event: FormEvent) => { event.preventDefault(); bidMutation.mutate(); };
  const user = userQuery.data;

  return <AppShell><div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" data-testid="auction-detail-page">
    <Link to="/" className="mb-7 inline-flex items-center gap-2 text-sm font-bold text-[#0f2c59] hover:text-[#c59b27] dark:text-[#f8e7aa]" data-testid="auction-detail-back-link"><ArrowLeft size={16} />Kembali ke katalog</Link>
    {auctionQuery.isError ? <div className="rounded-2xl border border-red-200 bg-red-50 p-10 text-center text-red-700" data-testid="auction-detail-error">Objek lelang tidak ditemukan.</div> : auction ? <div className="grid gap-8 lg:grid-cols-[1.15fr_0.85fr]">
      <section><div className="relative overflow-hidden rounded-2xl bg-[#0f2c59] text-white shadow-xl" data-testid="auction-detail-hero">{auction.image_url && <img src={auction.image_url} alt={`Foto ${auction.title}`} className="absolute inset-0 h-full w-full object-cover opacity-35" data-testid="auction-detail-image" />}<div className="absolute inset-0 bg-gradient-to-br from-[#0f2c59]/95 via-[#163b72]/85 to-[#0a1d3c]/90" /><div className="relative p-7 sm:p-10"><div className="absolute -right-10 -top-16 h-56 w-56 rounded-full border-[28px] border-[#c59b27]/15" /><div className="relative"><div className="flex flex-wrap items-center gap-2"><Badge className="border border-[#e5c158] bg-[#fef8ea] text-[#684f0e]" data-testid="auction-detail-status">{statusLabel(auction.status)}</Badge><span className="text-xs font-bold uppercase tracking-[0.15em] text-[#f8e7aa]" data-testid="auction-detail-category">{auction.category}</span></div><h1 className="mt-6 max-w-2xl text-3xl font-extrabold tracking-tight sm:text-5xl" data-testid="auction-detail-title">{auction.title}</h1><p className="mt-5 max-w-2xl text-base leading-relaxed text-slate-200" data-testid="auction-detail-description">{auction.description}</p><div className="mt-8 flex flex-wrap gap-4 text-sm text-slate-200"><span className="flex items-center gap-2" data-testid="auction-detail-location"><MapPin size={16} className="text-[#c59b27]" />{auction.location}</span><span className="flex items-center gap-2" data-testid="auction-detail-start"><CalendarDays size={16} className="text-[#c59b27]" />{formatDate(auction.starts_at)}</span></div></div></div>
        <div className="mt-8 grid gap-4 sm:grid-cols-3"><InfoTile label="Harga limit" value={formatRupiah(auction.limit_price)} testId="auction-detail-limit" /><InfoTile label="Penawaran tertinggi" value={formatRupiah(auction.highest_bid)} testId="auction-detail-highest" /><InfoTile label="Total penawaran" value={`${auction.bid_count} kali`} testId="auction-detail-bid-count" /></div>
        <Card className="mt-8 border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="bid-history-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="bid-history-title"><TrendingUp size={19} /> Riwayat penawaran</CardTitle></CardHeader><CardContent>{auction.bids.length === 0 ? <div className="p-6 text-center text-sm text-slate-500" data-testid="bid-history-empty">Belum ada penawaran. Jadilah peserta pertama.</div> : <div className="max-h-72 space-y-3 overflow-y-auto">{auction.bids.map((bid) => <BidRow bid={bid} key={bid.id} />)}</div>}</CardContent></Card>
      </section>
      <aside><Card className="sticky top-24 border-[#e5c158] shadow-lg shadow-[#c59b27]/10 dark:border-[#8a6b19] dark:bg-slate-900" data-testid="bid-panel"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="bid-panel-title"><Gavel size={19} /> Ikuti penawaran</CardTitle></CardHeader><CardContent><div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-center text-amber-900" data-testid="auction-countdown"><p className="text-[11px] font-bold uppercase tracking-[0.15em]">Sisa waktu</p><p className="mt-1 font-mono text-xl font-extrabold" data-testid="auction-countdown-value">{auction.status === "ended" ? "Lelang berakhir" : countdown}</p></div><div className="mt-5 rounded-lg bg-slate-50 p-4 dark:bg-slate-800" data-testid="minimum-bid-panel"><p className="text-xs text-slate-500">Minimum penawaran berikutnya</p><p className="mt-1 text-xl font-extrabold text-[#0f2c59] dark:text-white" data-testid="minimum-bid-value">{formatRupiah(minimum)}</p></div>
        {user?.role === "participant" && user.verification_status === "approved" && auction.status === "ongoing" ? <form onSubmit={submit} className="mt-5 space-y-4" data-testid="bid-form"><div className="space-y-2"><label htmlFor="bid-amount" className="text-sm font-bold text-slate-700 dark:text-slate-200">Nominal penawaran</label><Input id="bid-amount" type="number" min={minimum} step={auction.increment} value={amount} onChange={(event) => setAmount(event.target.value)} placeholder={String(minimum)} required data-testid="bid-amount-input" /></div>{bidMutation.isError && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700" data-testid="bid-error-message">{errorMessage(bidMutation.error)}</p>}<Button type="submit" className="h-11 w-full gap-2 bg-[#c59b27] font-extrabold text-[#0a1d3c] hover:bg-[#e5c158]" disabled={bidMutation.isPending} data-testid="submit-bid-button"><Gavel size={16} />{bidMutation.isPending ? "Mengirim…" : "Kirim penawaran"}</Button><p className="flex items-start gap-2 text-xs leading-relaxed text-slate-500" data-testid="bid-notice"><ShieldCheck size={14} className="mt-0.5 shrink-0 text-[#c59b27]" />Penawaran Anda tercatat dan memicu notifikasi email.</p></form> : user?.role === "participant" && user.verification_status !== "approved" ? <div className="mt-5 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900" data-testid="bid-verification-required"><IdCard size={18} /><p className="mt-2 font-bold">Verifikasi identitas diperlukan</p><p className="mt-1 text-xs leading-relaxed">Kirim KTP dan tunggu persetujuan petugas sebelum menawar.</p><Link to="/dashboard" className="mt-3 inline-flex font-bold underline" data-testid="bid-verification-link">Buka dashboard verifikasi</Link></div> : user ? <div className="mt-5 rounded-lg border border-slate-200 p-4 text-sm text-slate-500 dark:border-slate-700" data-testid="bid-not-available">Akun admin mengelola pengumuman, sedangkan penawaran dilakukan oleh peserta terverifikasi.</div> : <div className="mt-5 rounded-lg border border-[#e5c158] bg-[#fef8ea] p-4 text-sm text-[#684f0e]" data-testid="bid-login-prompt">Silakan masuk sebagai peserta untuk mengirim penawaran.<Link to="/auth" className="mt-3 block font-bold underline" data-testid="bid-login-link">Masuk atau daftar peserta</Link></div>}
      </CardContent></Card></aside>
    </div> : <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900" data-testid="auction-detail-loading">Memuat detail lelang…</div>}
  </div></AppShell>;
}

function InfoTile({ label, value, testId }: { label: string; value: string; testId: string }) { return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid={testId}><p className="text-xs font-semibold text-slate-500">{label}</p><p className="mt-2 text-lg font-extrabold text-[#0f2c59] dark:text-white" data-testid={`${testId}-value`}>{value}</p></div>; }
function BidRow({ bid }: { bid: Bid }) { return <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3 last:border-0 last:pb-0 dark:border-slate-700" data-testid={`bid-history-row-${bid.id}`}><div><p className="text-sm font-bold text-slate-700 dark:text-slate-200" data-testid={`bid-history-name-${bid.id}`}>{bid.bidder_name}</p><p className="mt-1 flex items-center gap-1 text-xs text-slate-400"><Clock3 size={12} />{formatDate(bid.created_at)}</p></div><span className="font-extrabold text-[#c59b27]" data-testid={`bid-history-amount-${bid.id}`}>{formatRupiah(bid.amount)}</span></div>; }