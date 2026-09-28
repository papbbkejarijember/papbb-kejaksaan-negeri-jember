import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BarChart3, CalendarClock, CheckCircle2, FileCheck2, FilePlus2, FileText, Gavel, MapPin, Pencil, Plus, ShieldCheck, Tag, UserCheck, UserX, X } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiGet, apiPatch, apiPost, ApiError } from "@/lib/api";
import { formatDate, formatRupiah, statusLabel } from "@/lib/format";
import type { AdminDashboard as AdminDashboardData, Auction, AuctionCreatePayload, IdentitySubmission, NotificationConfig, User } from "@/lib/types";

const blankForm: AuctionCreatePayload = { title: "", category: "Kendaraan", description: "", location: "", limit_price: 0, increment: 0, starts_at: "", ends_at: "" };

function errorMessage(error: unknown) {
  if (error instanceof ApiError && typeof error.body === "object" && error.body && "detail" in error.body) return String(error.body.detail);
  return "Periksa kembali data yang dimasukkan.";
}

function toLocalInput(value: string) {
  return new Date(value).toISOString().slice(0, 16);
}

export default function Admin() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AuctionCreatePayload>(blankForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const userQuery = useQuery({ queryKey: ["current-user"], queryFn: () => apiGet<User | null>("/auth/me"), retry: false });
  const isAdmin = userQuery.data?.role === "admin";
  const dashboardQuery = useQuery({ queryKey: ["admin-dashboard"], queryFn: () => apiGet<AdminDashboardData>("/auctions/dashboard/admin"), enabled: isAdmin, retry: false });
  const verificationsQuery = useQuery({ queryKey: ["identity-verifications"], queryFn: () => apiGet<IdentitySubmission[]>("/auth/verifications"), enabled: isAdmin, retry: false });
  const configQuery = useQuery({ queryKey: ["notification-config"], queryFn: () => apiGet<NotificationConfig>("/notifications/config"), retry: false });

  useEffect(() => {
    if (!userQuery.isFetched) return;
    if (!userQuery.data || userQuery.data.role !== "admin") navigate("/auth");
  }, [navigate, userQuery.data, userQuery.isFetched]);

  const refreshAuctions = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-dashboard"] });
    await queryClient.invalidateQueries({ queryKey: ["auctions"] });
    await queryClient.invalidateQueries({ queryKey: ["auction-results"] });
  };
  const createMutation = useMutation({
    mutationFn: () => apiPost<Auction>("/auctions", { ...form, limit_price: Number(form.limit_price), increment: Number(form.increment) }),
    onSuccess: async () => { await refreshAuctions(); toast.success("Pengumuman lelang berhasil dibuat."); setForm(blankForm); },
  });
  const updateMutation = useMutation({
    mutationFn: () => apiPatch<Auction>(`/auctions/${editingId}`, { ...form, limit_price: Number(form.limit_price), increment: Number(form.increment) }),
    onSuccess: async () => { await refreshAuctions(); toast.success("Perubahan lelang berhasil disimpan."); setEditingId(null); setForm(blankForm); },
  });
  const closeMutation = useMutation({
    mutationFn: (auctionId: string) => apiPost<Auction>(`/auctions/${auctionId}/close`),
    onSuccess: async () => { await refreshAuctions(); toast.success("Lelang ditutup dan hasil dipublikasikan."); },
  });
  const reviewMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "approved" | "rejected" }) => apiPatch<IdentitySubmission>(`/auth/verifications/${id}`, { status, review_note: status === "rejected" ? "Dokumen belum jelas atau data tidak sesuai." : null }),
    onSuccess: async (_, variables) => { await queryClient.invalidateQueries({ queryKey: ["identity-verifications"] }); toast.success(variables.status === "approved" ? "Identitas peserta disetujui." : "Pengajuan peserta ditolak."); },
  });

  const data = dashboardQuery.data;
  const update = (key: keyof AuctionCreatePayload, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const submit = (event: FormEvent) => { event.preventDefault(); if (editingId) updateMutation.mutate(); else createMutation.mutate(); };
  const editAuction = (auction: Auction) => {
    setEditingId(auction.id);
    setForm({ title: auction.title, category: auction.category, description: auction.description, location: auction.location, limit_price: auction.limit_price, increment: auction.increment, starts_at: toLocalInput(auction.starts_at), ends_at: toLocalInput(auction.ends_at) });
    window.scrollTo({ top: 240, behavior: "smooth" });
  };
  const cancelEdit = () => { setEditingId(null); setForm(blankForm); };
  const pending = (verificationsQuery.data ?? []).filter((item) => item.status === "pending");
  const saving = createMutation.isPending || updateMutation.isPending;

  return <AppShell><div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" data-testid="admin-page">
    <div className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between dark:border-slate-700"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#c59b27]" data-testid="admin-kicker">Ruang petugas</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight text-[#0f2c59] dark:text-white" data-testid="admin-page-title">Panel pengelola lelang</h1><p className="mt-2 text-sm text-slate-500" data-testid="admin-page-description">Kelola objek, verifikasi peserta, penutupan, dan berita acara lelang Kejari Jember.</p></div><div className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-bold ${configQuery.data?.email_mode === "brevo" ? "border-green-200 bg-green-50 text-green-800" : "border-[#e5c158] bg-[#fef8ea] text-[#684f0e]"}`} data-testid="admin-notification-status"><ShieldCheck size={15} />Email: {configQuery.data?.email_mode === "brevo" ? "BREVO AKTIF" : "DEMO MOCK"} · WhatsApp: MOCK</div></div>
    <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="admin-stats">{[{ key: "total", label: "Total objek", value: data?.total_auctions ?? 0, icon: <BarChart3 size={18} /> }, { key: "ongoing", label: "Berlangsung", value: data?.ongoing_auctions ?? 0, icon: <Gavel size={18} /> }, { key: "upcoming", label: "Akan datang", value: data?.upcoming_auctions ?? 0, icon: <CalendarClock size={18} /> }, { key: "ended", label: "Selesai", value: data?.ended_auctions ?? 0, icon: <CheckCircle2 size={18} /> }].map((item) => <div key={item.key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid={`admin-stat-${item.key}`}><span className="grid h-9 w-9 place-items-center rounded-lg bg-[#eff4fb] text-[#0f2c59] dark:bg-slate-800 dark:text-[#f8e7aa]">{item.icon}</span><p className="mt-4 text-3xl font-extrabold text-[#0f2c59] dark:text-white" data-testid={`admin-stat-${item.key}-value`}>{item.value}</p><p className="text-sm font-semibold text-slate-500" data-testid={`admin-stat-${item.key}-label`}>{item.label}</p></div>)}</div>

    <div className="grid gap-8 lg:grid-cols-[0.82fr_1.18fr]">
      <Card className="h-fit border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="admin-create-card"><CardHeader className="flex-row items-center justify-between"><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="admin-create-title"><FilePlus2 size={19} /> {editingId ? "Edit pengumuman" : "Buat pengumuman lelang"}</CardTitle>{editingId && <Button variant="ghost" size="sm" onClick={cancelEdit} data-testid="admin-cancel-edit-button"><X size={15} />Batal</Button>}</CardHeader><CardContent><form onSubmit={submit} className="space-y-4" data-testid="admin-create-form"><Field label="Nama objek" id="auction-title" value={form.title} onChange={(value) => update("title", value)} placeholder="Contoh: Toyota Innova 2018" testId="admin-auction-title-input" /><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="auction-category">Kategori</Label><select id="auction-category" value={form.category} onChange={(event) => update("category", event.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" data-testid="admin-auction-category-select"><option>Kendaraan</option><option>Elektronik</option><option>Properti</option><option>Barang Sitaan Lain</option></select></div><Field label="Lokasi" id="auction-location" value={form.location} onChange={(value) => update("location", value)} placeholder="Jember" testId="admin-auction-location-input" /></div><div className="space-y-2"><Label htmlFor="auction-description">Deskripsi</Label><textarea id="auction-description" value={form.description} onChange={(event) => update("description", event.target.value)} className="min-h-24 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" placeholder="Jelaskan kondisi dan kelengkapan objek…" required data-testid="admin-auction-description-input" /></div><div className="grid gap-4 sm:grid-cols-2"><Field label="Harga limit (Rp)" id="auction-limit" type="number" value={String(form.limit_price || "")} onChange={(value) => update("limit_price", value)} placeholder="15000000" testId="admin-auction-limit-input" /><Field label="Kelipatan (Rp)" id="auction-increment" type="number" value={String(form.increment || "")} onChange={(value) => update("increment", value)} placeholder="500000" testId="admin-auction-increment-input" /></div><div className="grid gap-4 sm:grid-cols-2"><Field label="Mulai" id="auction-start" type="datetime-local" value={form.starts_at} onChange={(value) => update("starts_at", value)} testId="admin-auction-start-input" /><Field label="Berakhir" id="auction-end" type="datetime-local" value={form.ends_at} onChange={(value) => update("ends_at", value)} testId="admin-auction-end-input" /></div>{(createMutation.isError || updateMutation.isError) && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" data-testid="admin-save-error">{errorMessage(createMutation.error ?? updateMutation.error)}</p>}<Button type="submit" className="h-11 w-full gap-2 bg-[#0f2c59] font-bold hover:bg-[#163b72]" disabled={saving} data-testid="admin-create-auction-button"><Plus size={16} />{saving ? "Menyimpan…" : editingId ? "Simpan perubahan" : "Publikasikan lelang"}</Button></form></CardContent></Card>

      <Card className="border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="admin-auctions-card"><CardHeader className="flex-row items-center justify-between"><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="admin-auctions-title"><Gavel size={19} /> Daftar objek</CardTitle><Link to="/" className="text-xs font-bold text-[#0f2c59] hover:text-[#c59b27] dark:text-[#f8e7aa]" data-testid="admin-public-catalog-link">Lihat publik</Link></CardHeader><CardContent>{!data || data.auctions.length === 0 ? <div className="rounded-xl border-2 border-dashed border-slate-300 p-12 text-center dark:border-slate-600" data-testid="admin-auctions-empty"><Gavel className="mx-auto text-slate-400" size={30} /><p className="mt-4 font-bold text-[#0f2c59] dark:text-white" data-testid="admin-auctions-empty-title">Belum ada objek lelang</p><p className="mt-1 text-sm text-slate-500" data-testid="admin-auctions-empty-description">Gunakan formulir di samping untuk membuat pengumuman pertama.</p></div> : <div className="space-y-3">{data.auctions.map((auction) => <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700" key={auction.id} data-testid={`admin-auction-row-${auction.id}`}><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold text-[#0f2c59] dark:text-white" data-testid={`admin-auction-row-title-${auction.id}`}>{auction.title}</p><div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500"><span className="flex items-center gap-1"><Tag size={13} />{auction.category}</span><span className="flex items-center gap-1"><MapPin size={13} />{auction.location}</span></div></div><Badge variant="outline" data-testid={`admin-auction-row-status-${auction.id}`}>{statusLabel(auction.status)}</Badge></div><div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-slate-700"><span>Limit <strong className="text-slate-700 dark:text-slate-300">{formatRupiah(auction.limit_price)}</strong></span><span>{formatDate(auction.starts_at)}</span></div><div className="mt-3 flex flex-wrap gap-2"><Link to={`/lelang/${auction.id}`} className="inline-flex h-8 items-center rounded-md border border-slate-200 px-3 text-xs font-bold text-[#0f2c59] dark:border-slate-700 dark:text-[#f8e7aa]" data-testid={`admin-auction-row-detail-${auction.id}`}>Detail</Link>{auction.status !== "ended" && <><Button variant="outline" size="sm" onClick={() => editAuction(auction)} data-testid={`admin-edit-auction-${auction.id}`}><Pencil size={13} />Edit</Button><Button variant="outline" size="sm" onClick={() => closeMutation.mutate(auction.id)} disabled={closeMutation.isPending} data-testid={`admin-close-auction-${auction.id}`}><FileCheck2 size={13} />Tutup</Button></>}<Link to={`/admin/berita-acara/${auction.id}`} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-3 text-xs font-bold text-[#0f2c59] dark:border-slate-700 dark:text-[#f8e7aa]" data-testid={`admin-report-link-${auction.id}`}><FileText size={13} />Berita acara</Link></div></div>)}</div>}</CardContent></Card>
    </div>

    <Card className="mt-8 border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="admin-verifications-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="admin-verifications-title"><UserCheck size={19} /> Verifikasi identitas peserta <Badge variant="outline" data-testid="pending-verification-count">{pending.length} menunggu</Badge></CardTitle></CardHeader><CardContent>{pending.length === 0 ? <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-600" data-testid="admin-verifications-empty">Tidak ada pengajuan KTP yang menunggu pemeriksaan.</div> : <div className="grid gap-5 lg:grid-cols-2">{pending.map((item) => <div className="grid gap-4 rounded-xl border border-slate-200 p-4 sm:grid-cols-[150px_1fr] dark:border-slate-700" key={item.id} data-testid={`verification-card-${item.id}`}><img src={item.ktp_image_data} alt={`KTP ${item.full_name}`} className="h-28 w-full rounded-lg bg-slate-100 object-cover" data-testid={`verification-image-${item.id}`} /><div><p className="font-bold text-[#0f2c59] dark:text-white" data-testid={`verification-name-${item.id}`}>{item.full_name}</p><p className="mt-1 text-xs text-slate-500" data-testid={`verification-email-${item.id}`}>{item.email}</p><p className="mt-2 text-sm" data-testid={`verification-nik-${item.id}`}>NIK: {item.nik}</p><p className="mt-1 text-xs leading-relaxed text-slate-500" data-testid={`verification-address-${item.id}`}>{item.address}</p><div className="mt-3 flex gap-2"><Button size="sm" onClick={() => reviewMutation.mutate({ id: item.id, status: "approved" })} data-testid={`approve-verification-${item.id}`}><UserCheck size={14} />Setujui</Button><Button variant="outline" size="sm" onClick={() => reviewMutation.mutate({ id: item.id, status: "rejected" })} data-testid={`reject-verification-${item.id}`}><UserX size={14} />Tolak</Button></div></div></div>)}</div>}</CardContent></Card>
  </div></AppShell>;
}

function Field({ label, id, value, onChange, placeholder, type = "text", testId }: { label: string; id: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string; testId: string }) {
  return <div className="space-y-2"><Label htmlFor={id}>{label}</Label><Input id={id} type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} required className="h-10" data-testid={testId} /></div>;
}