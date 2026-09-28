import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, ChevronRight, Clock3, FileCheck2, Gavel, IdCard, Mail, MessageCircle, Send, ShieldCheck, Trophy, Upload } from "lucide-react";
import { useEffect, useState, type ChangeEvent, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiGet, apiPost } from "@/lib/api";
import { formatDate, formatRupiah } from "@/lib/format";
import type { IdentitySubmission, NotificationChannel, NotificationConfig, NotificationStatus, NotificationTestResponse, ParticipantDashboard as ParticipantDashboardData, User, VerificationStatus } from "@/lib/types";

const statusCopy: Record<VerificationStatus, { label: string; description: string; className: string }> = {
  not_submitted: { label: "Belum diajukan", description: "Unggah KTP untuk memperoleh hak mengikuti penawaran.", className: "border-amber-200 bg-amber-50 text-amber-800" },
  pending: { label: "Menunggu verifikasi", description: "Petugas sedang memeriksa identitas yang Anda kirim.", className: "border-blue-200 bg-blue-50 text-blue-800" },
  approved: { label: "Terverifikasi", description: "Identitas disetujui. Anda dapat mengikuti penawaran.", className: "border-green-200 bg-green-50 text-green-800" },
  rejected: { label: "Perlu diperbaiki", description: "Pengajuan ditolak. Periksa dokumen lalu kirim ulang.", className: "border-red-200 bg-red-50 text-red-800" },
};

export default function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [channels, setChannels] = useState<NotificationChannel[]>(["email"]);
  const [message, setMessage] = useState("Ini adalah uji notifikasi dari Portal Lelang Kejari Jember.");
  const [nik, setNik] = useState("");
  const [address, setAddress] = useState("");
  const [ktpImage, setKtpImage] = useState("");
  const [fileName, setFileName] = useState("");
  const userQuery = useQuery({ queryKey: ["current-user"], queryFn: () => apiGet<User | null>("/auth/me"), retry: false });
  const dashboardQuery = useQuery({ queryKey: ["participant-dashboard"], queryFn: () => apiGet<ParticipantDashboardData>("/auctions/dashboard/participant"), enabled: userQuery.data?.role === "participant", retry: false, refetchInterval: 15_000 });
  const configQuery = useQuery({ queryKey: ["notification-config"], queryFn: () => apiGet<NotificationConfig>("/notifications/config"), retry: false });
  const notificationMutation = useMutation({
    mutationFn: () => apiPost<NotificationTestResponse>("/notifications/test", { channels, subject: "Uji notifikasi lelang", message }),
    onSuccess: async (result) => { await queryClient.invalidateQueries({ queryKey: ["participant-dashboard"] }); result.status === "failed" ? toast.error("Brevo menolak pengiriman. Periksa verifikasi sender.") : toast.success(result.status === "submitted" ? "Email berhasil diserahkan ke Brevo." : "Notifikasi mock berhasil dicatat."); },
  });
  const identityMutation = useMutation({
    mutationFn: () => apiPost<IdentitySubmission>("/auth/identity", { nik, address, ktp_image_data: ktpImage }),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["current-user"] }); await queryClient.invalidateQueries({ queryKey: ["participant-dashboard"] }); toast.success("Dokumen KTP berhasil dikirim untuk verifikasi."); },
  });

  useEffect(() => {
    if (!userQuery.isFetched) return;
    if (!userQuery.data) navigate("/auth");
    if (userQuery.data?.role === "admin") navigate("/admin");
  }, [navigate, userQuery.data, userQuery.isFetched]);

  const data = dashboardQuery.data;
  const toggleChannel = (channel: NotificationChannel) => setChannels((current) => current.includes(channel) ? current.filter((item) => item !== channel) : [...current, channel]);
  const submitNotification = (event: FormEvent) => { event.preventDefault(); notificationMutation.mutate(); };
  const submitIdentity = (event: FormEvent) => { event.preventDefault(); identityMutation.mutate(); };
  const selectKtp = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => setKtpImage(String(reader.result));
    reader.readAsDataURL(file);
  };

  return <AppShell><div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" data-testid="participant-dashboard-page">
    <div className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between dark:border-slate-700"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#c59b27]" data-testid="participant-dashboard-kicker">Ruang peserta</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight text-[#0f2c59] dark:text-white" data-testid="participant-dashboard-title">Dashboard peserta</h1><p className="mt-2 text-sm text-slate-500" data-testid="participant-dashboard-welcome">Pantau verifikasi, penawaran, dan pemberitahuan lelang Anda dalam satu tempat.</p></div><Link to="/" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[#0f2c59] px-4 text-sm font-bold text-white transition-colors hover:bg-[#163b72]" data-testid="participant-browse-auctions-link">Lihat katalog <ChevronRight size={16} /></Link></div>
    {data ? <>
      <div className="mb-8 grid gap-4 sm:grid-cols-3" data-testid="participant-stats"><Stat icon={<Gavel size={19} />} label="Total penawaran" value={String(data.active_bids)} testId="participant-stat-bids" /><Stat icon={<Trophy size={19} />} label="Lelang dimenangkan" value={String(data.won_auctions)} testId="participant-stat-won" /><Stat icon={<Bell size={19} />} label="Pemberitahuan" value={String(data.total_notifications)} testId="participant-stat-notifications" /></div>
      <Card className="mb-8 border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="identity-verification-card"><CardHeader className="flex-row items-center justify-between"><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="identity-verification-title"><IdCard size={19} /> Verifikasi identitas</CardTitle><Badge className={`border ${statusCopy[data.user.verification_status].className}`} data-testid="identity-verification-status">{statusCopy[data.user.verification_status].label}</Badge></CardHeader><CardContent><p className="text-sm text-slate-500" data-testid="identity-verification-description">{statusCopy[data.user.verification_status].description}</p>{(data.user.verification_status === "not_submitted" || data.user.verification_status === "rejected") && <form onSubmit={submitIdentity} className="mt-5 grid gap-4 lg:grid-cols-2" data-testid="identity-verification-form"><div className="space-y-2"><Label htmlFor="identity-nik">NIK (16 angka)</Label><Input id="identity-nik" value={nik} onChange={(event) => setNik(event.target.value.replace(/\D/g, "").slice(0, 16))} minLength={16} maxLength={16} inputMode="numeric" required data-testid="identity-nik-input" /></div><div className="space-y-2"><Label htmlFor="identity-file">Foto KTP</Label><label htmlFor="identity-file" className="flex h-10 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm text-slate-500" data-testid="identity-file-label"><Upload size={15} />{fileName || "Pilih JPG, PNG, atau WEBP"}</label><input id="identity-file" type="file" accept="image/jpeg,image/png,image/webp" onChange={selectKtp} className="sr-only" required data-testid="identity-file-input" /></div><div className="space-y-2 lg:col-span-2"><Label htmlFor="identity-address">Alamat sesuai KTP</Label><textarea id="identity-address" value={address} onChange={(event) => setAddress(event.target.value)} className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" required data-testid="identity-address-input" /></div><Button type="submit" className="gap-2 bg-[#0f2c59] font-bold lg:col-span-2" disabled={!ktpImage || identityMutation.isPending} data-testid="identity-submit-button"><FileCheck2 size={16} />{identityMutation.isPending ? "Mengirim…" : "Kirim untuk verifikasi"}</Button></form>}</CardContent></Card>
      <div className="grid gap-8 lg:grid-cols-[1.25fr_0.75fr]"><Card className="border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="participant-bids-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="participant-bids-title"><Gavel size={19} /> Riwayat penawaran</CardTitle></CardHeader><CardContent>{data.bids.length === 0 ? <EmptyPanel icon={<Gavel size={24} />} title="Belum ada penawaran" description="Ikuti lelang yang sedang berlangsung dari katalog publik." testId="participant-bids-empty" /> : <div className="space-y-3">{data.bids.map((bid) => <div className="flex flex-col gap-2 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700" key={bid.id} data-testid={`participant-bid-row-${bid.id}`}><div><p className="font-bold text-[#0f2c59] dark:text-white" data-testid={`participant-bid-name-${bid.id}`}>Penawaran lelang</p><p className="mt-1 flex items-center gap-1 text-xs text-slate-500"><Clock3 size={13} />{formatDate(bid.created_at)}</p></div><span className="font-extrabold text-[#c59b27]" data-testid={`participant-bid-amount-${bid.id}`}>{formatRupiah(bid.amount)}</span></div>)}</div>}</CardContent></Card>
        <div className="space-y-8"><Card className="border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="notification-test-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="notification-test-title"><Bell size={19} /> Uji notifikasi</CardTitle></CardHeader><CardContent><form onSubmit={submitNotification} className="space-y-4" data-testid="notification-test-form"><p className="text-xs leading-relaxed text-slate-500" data-testid="notification-test-description">Email {configQuery.data?.email_mode === "brevo" ? `aktif melalui Brevo (${configQuery.data.sender_email})` : "menggunakan MOCK"}. WhatsApp masih DEMO MOCK.</p><div className="grid grid-cols-2 gap-2"><ChannelButton checked={channels.includes("email")} onChange={() => toggleChannel("email")} icon={<Mail size={15} />} label="Email" testId="notification-email-toggle" /><ChannelButton checked={channels.includes("whatsapp")} onChange={() => toggleChannel("whatsapp")} icon={<MessageCircle size={15} />} label="WhatsApp" testId="notification-whatsapp-toggle" /></div><textarea value={message} onChange={(event) => setMessage(event.target.value)} className="min-h-24 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" aria-label="Pesan notifikasi" data-testid="notification-message-input" /><Button type="submit" className="h-10 w-full gap-2 bg-[#0f2c59] font-bold hover:bg-[#163b72]" disabled={channels.length === 0 || notificationMutation.isPending} data-testid="notification-send-button"><Send size={15} />{notificationMutation.isPending ? "Memproses…" : "Kirim uji kanal"}</Button></form></CardContent></Card><Card className="border-[#e5c158] bg-[#fef8ea] shadow-sm dark:border-[#8a6b19] dark:bg-[#2c2613]" data-testid="participant-security-card"><CardContent className="p-5"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 text-[#c59b27]" size={19} /><div><p className="font-bold text-[#684f0e] dark:text-[#f8e7aa]" data-testid="participant-security-title">Aktivitas terverifikasi</p><p className="mt-1 text-xs leading-relaxed text-[#8a6b19] dark:text-[#e5c158]" data-testid="participant-security-description">Setiap verifikasi, penawaran, dan pemberitahuan dicatat untuk menjaga transparansi proses.</p></div></div></CardContent></Card></div>
      </div>
      <Card className="mt-8 border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="notification-history-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="notification-history-title"><Bell size={19} /> Riwayat pemberitahuan <span className="text-xs font-normal text-slate-400">diperbarui otomatis</span></CardTitle></CardHeader><CardContent>{data.notifications.length === 0 ? <EmptyPanel icon={<Bell size={24} />} title="Belum ada pemberitahuan" description="Pemberitahuan penawaran dan kanal akan tampil di sini." testId="notification-history-empty" /> : <div className="grid gap-3 md:grid-cols-2">{data.notifications.map((notification) => <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700" key={notification.id} data-testid={`notification-row-${notification.id}`}><div className="flex items-center justify-between gap-3"><p className="font-bold text-[#0f2c59] dark:text-white" data-testid={`notification-subject-${notification.id}`}>{notification.subject}</p><Badge variant="outline" data-testid={`notification-status-${notification.id}`}>{notification.provider.toUpperCase()} · {notificationStatusLabel(notification.status)}</Badge></div><p className="mt-2 text-sm text-slate-500" data-testid={`notification-message-${notification.id}`}>{notification.message}</p><p className="mt-3 text-xs text-slate-400" data-testid={`notification-channel-${notification.id}`}>{notification.channel === "email" ? "Email" : "WhatsApp"} · {formatDate(notification.created_at)}</p>{notification.status_history.length > 0 && <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 dark:border-slate-700" data-testid={`notification-timeline-${notification.id}`}>{notification.status_history.slice(-3).reverse().map((event, index) => <div className="flex items-center justify-between gap-3 text-xs" key={`${event.at}-${index}`} data-testid={`notification-event-${notification.id}-${index}`}><span className="flex items-center gap-2 font-semibold text-slate-600 dark:text-slate-300"><span className="h-2 w-2 rounded-full bg-[#c59b27]" />{notificationStatusLabel(event.status)}</span><span className="text-slate-400">{formatDate(event.at)}</span></div>)}</div>}</div>)}</div>}</CardContent></Card>
    </> : <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center text-sm text-amber-900" data-testid="participant-dashboard-loading">Memuat data ruang peserta…</div>}
  </div></AppShell>;
}

function Stat({ icon, label, value, testId }: { icon: ReactNode; label: string; value: string; testId: string }) { return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid={testId}><div className="flex items-center justify-between"><span className="grid h-9 w-9 place-items-center rounded-lg bg-[#eff4fb] text-[#0f2c59] dark:bg-slate-800 dark:text-[#f8e7aa]">{icon}</span><span className="text-3xl font-extrabold text-[#0f2c59] dark:text-white" data-testid={`${testId}-value`}>{value}</span></div><p className="mt-4 text-sm font-semibold text-slate-500" data-testid={`${testId}-label`}>{label}</p></div>; }
function EmptyPanel({ icon, title, description, testId }: { icon: ReactNode; title: string; description: string; testId: string }) { return <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-600" data-testid={testId}><span className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800">{icon}</span><p className="mt-3 font-bold text-[#0f2c59] dark:text-white" data-testid={`${testId}-title`}>{title}</p><p className="mt-1 text-xs text-slate-500" data-testid={`${testId}-description`}>{description}</p></div>; }
function ChannelButton({ checked, onChange, icon, label, testId }: { checked: boolean; onChange: () => void; icon: ReactNode; label: string; testId: string }) { return <button type="button" aria-pressed={checked} onClick={onChange} className={`flex min-h-10 w-full items-center gap-2 rounded-lg border px-3 py-2 text-sm font-bold transition-colors ${checked ? "border-[#c59b27] bg-[#fef8ea] text-[#684f0e]" : "border-slate-200 text-slate-500 dark:border-slate-700"}`} data-testid={testId}>{icon}{label}</button>; }

function notificationStatusLabel(status: NotificationStatus) {
  return {
    simulated: "Simulasi",
    submitted: "Dikirim ke Brevo",
    delivered: "Terkirim",
    opened: "Dibuka",
    soft_bounce: "Tertunda",
    hard_bounce: "Gagal permanen",
    blocked: "Diblokir",
    invalid: "Alamat tidak valid",
    failed: "Gagal",
  }[status];
}