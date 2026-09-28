import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCircle2, ChevronRight, Clock3, Gavel, Mail, MessageCircle, Send, ShieldCheck, Trophy, UserRound } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet, apiPost } from "@/lib/api";
import { formatDate, formatRupiah } from "@/lib/format";
import type { NotificationChannel, ParticipantDashboard as ParticipantDashboardData, User } from "@/lib/types";

export default function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const userQuery = useQuery({ queryKey: ["current-user"], queryFn: () => apiGet<User | null>("/auth/me"), retry: false });
  const dashboardQuery = useQuery({ queryKey: ["participant-dashboard"], queryFn: () => apiGet<ParticipantDashboardData>("/auctions/dashboard/participant"), enabled: userQuery.data?.role === "participant", retry: false });
  const [channels, setChannels] = useState<NotificationChannel[]>(["email"]);
  const [message, setMessage] = useState("Ini adalah uji notifikasi dari Portal Lelang Kejari Jember.");
  const notificationMutation = useMutation({
    mutationFn: () => apiPost<{ status: string }>("/notifications/test", { channels, subject: "Uji notifikasi lelang", message }),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["participant-dashboard"] }); toast.success("Notifikasi demo tercatat sebagai simulasi."); },
  });

  useEffect(() => {
    if (!userQuery.isFetched) return;
    if (!userQuery.data) navigate("/auth");
    if (userQuery.data?.role === "admin") navigate("/admin");
  }, [navigate, userQuery.data, userQuery.isFetched]);

  const data = dashboardQuery.data;
  const toggleChannel = (channel: NotificationChannel) => setChannels((current) => current.includes(channel) ? current.filter((item) => item !== channel) : [...current, channel]);
  const submitNotification = (event: FormEvent) => { event.preventDefault(); notificationMutation.mutate(); };

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8" data-testid="participant-dashboard-page">
        <div className="mb-8 flex flex-col gap-4 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between dark:border-slate-700">
          <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-[#c59b27]" data-testid="participant-dashboard-kicker">Ruang peserta</p><h1 className="mt-2 text-3xl font-extrabold tracking-tight text-[#0f2c59] dark:text-white" data-testid="participant-dashboard-title">Dashboard peserta</h1><p className="mt-2 text-sm text-slate-500" data-testid="participant-dashboard-welcome">Pantau penawaran dan pemberitahuan lelang Anda dalam satu tempat.</p></div>
          <Link to="/" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-[#0f2c59] px-4 text-sm font-bold text-white transition-colors hover:bg-[#163b72]" data-testid="participant-browse-auctions-link">Lihat katalog <ChevronRight size={16} /></Link>
        </div>
        {data ? <>
          <div className="mb-8 grid gap-4 sm:grid-cols-3" data-testid="participant-stats"><Stat icon={<Gavel size={19} />} label="Total penawaran" value={String(data.active_bids)} testId="participant-stat-bids" /><Stat icon={<Trophy size={19} />} label="Lelang dimenangkan" value={String(data.won_auctions)} testId="participant-stat-won" /><Stat icon={<Bell size={19} />} label="Pemberitahuan" value={String(data.total_notifications)} testId="participant-stat-notifications" /></div>
          <div className="grid gap-8 lg:grid-cols-[1.25fr_0.75fr]">
            <Card className="border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="participant-bids-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="participant-bids-title"><Gavel size={19} /> Riwayat penawaran</CardTitle></CardHeader><CardContent>{data.bids.length === 0 ? <EmptyPanel icon={<Gavel size={24} />} title="Belum ada penawaran" description="Ikuti lelang yang sedang berlangsung dari katalog publik." testId="participant-bids-empty" /> : <div className="space-y-3">{data.bids.map((bid) => <div className="flex flex-col gap-2 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-700" key={bid.id} data-testid={`participant-bid-row-${bid.id}`}><div><p className="font-bold text-[#0f2c59] dark:text-white" data-testid={`participant-bid-name-${bid.id}`}>Penawaran lelang</p><p className="mt-1 flex items-center gap-1 text-xs text-slate-500"><Clock3 size={13} />{formatDate(bid.created_at)}</p></div><span className="font-extrabold text-[#c59b27]" data-testid={`participant-bid-amount-${bid.id}`}>{formatRupiah(bid.amount)}</span></div>)}</div>}</CardContent></Card>
            <div className="space-y-8"><Card className="border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="notification-test-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="notification-test-title"><Bell size={19} /> Uji notifikasi</CardTitle></CardHeader><CardContent><form onSubmit={submitNotification} className="space-y-4" data-testid="notification-test-form"><p className="text-xs leading-relaxed text-slate-500" data-testid="notification-test-description">Mode DEMO MOCK aktif. Simulasi tercatat di dashboard tanpa mengirim pesan eksternal.</p><div className="grid grid-cols-2 gap-2"><ChannelButton channel="email" checked={channels.includes("email")} onChange={() => toggleChannel("email")} icon={<Mail size={15} />} label="Email" testId="notification-email-toggle" /><ChannelButton channel="whatsapp" checked={channels.includes("whatsapp")} onChange={() => toggleChannel("whatsapp")} icon={<MessageCircle size={15} />} label="WhatsApp" testId="notification-whatsapp-toggle" /></div><textarea value={message} onChange={(event) => setMessage(event.target.value)} className="min-h-24 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[#c59b27]" aria-label="Pesan notifikasi" data-testid="notification-message-input" /><Button type="submit" className="h-10 w-full gap-2 bg-[#0f2c59] font-bold hover:bg-[#163b72]" disabled={channels.length === 0 || notificationMutation.isPending} data-testid="notification-send-button"><Send size={15} />{notificationMutation.isPending ? "Mencatat…" : "Catat simulasi"}</Button></form></CardContent></Card><Card className="border-[#e5c158] bg-[#fef8ea] shadow-sm dark:border-[#8a6b19] dark:bg-[#2c2613]" data-testid="participant-security-card"><CardContent className="p-5"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 text-[#c59b27]" size={19} /><div><p className="font-bold text-[#684f0e] dark:text-[#f8e7aa]" data-testid="participant-security-title">Aktivitas terverifikasi</p><p className="mt-1 text-xs leading-relaxed text-[#8a6b19] dark:text-[#e5c158]" data-testid="participant-security-description">Setiap penawaran dan pemberitahuan dicatat untuk menjaga transparansi proses lelang.</p></div></div></CardContent></Card></div>
          </div>
          <Card className="mt-8 border-slate-200 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid="notification-history-card"><CardHeader><CardTitle className="flex items-center gap-2 text-lg text-[#0f2c59] dark:text-white" data-testid="notification-history-title"><Bell size={19} /> Riwayat pemberitahuan</CardTitle></CardHeader><CardContent>{data.notifications.length === 0 ? <EmptyPanel icon={<Bell size={24} />} title="Belum ada pemberitahuan" description="Pemberitahuan penawaran dan simulasi kanal akan tampil di sini." testId="notification-history-empty" /> : <div className="grid gap-3 md:grid-cols-2">{data.notifications.map((notification) => <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700" key={notification.id} data-testid={`notification-row-${notification.id}`}><div className="flex items-center justify-between gap-3"><p className="font-bold text-[#0f2c59] dark:text-white" data-testid={`notification-subject-${notification.id}`}>{notification.subject}</p><Badge variant="outline" data-testid={`notification-status-${notification.id}`}>MOCK</Badge></div><p className="mt-2 text-sm text-slate-500" data-testid={`notification-message-${notification.id}`}>{notification.message}</p><p className="mt-3 text-xs text-slate-400" data-testid={`notification-channel-${notification.id}`}>{notification.channel === "email" ? "Email" : "WhatsApp"} · {formatDate(notification.created_at)}</p></div>)}</div>}</CardContent></Card>
        </> : <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center text-sm text-amber-900" data-testid="participant-dashboard-loading">Memuat data ruang peserta…</div>}
      </div>
    </AppShell>
  );
}

function Stat({ icon, label, value, testId }: { icon: React.ReactNode; label: string; value: string; testId: string }) { return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid={testId}><div className="flex items-center justify-between"><span className="grid h-9 w-9 place-items-center rounded-lg bg-[#eff4fb] text-[#0f2c59] dark:bg-slate-800 dark:text-[#f8e7aa]">{icon}</span><span className="text-3xl font-extrabold text-[#0f2c59] dark:text-white" data-testid={`${testId}-value`}>{value}</span></div><p className="mt-4 text-sm font-semibold text-slate-500" data-testid={`${testId}-label`}>{label}</p></div>; }
function EmptyPanel({ icon, title, description, testId }: { icon: React.ReactNode; title: string; description: string; testId: string }) { return <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-600" data-testid={testId}><span className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800">{icon}</span><p className="mt-3 font-bold text-[#0f2c59] dark:text-white" data-testid={`${testId}-title`}>{title}</p><p className="mt-1 text-xs text-slate-500" data-testid={`${testId}-description`}>{description}</p></div>; }
function ChannelButton({ checked, onChange, icon, label, testId }: { channel: NotificationChannel; checked: boolean; onChange: () => void; icon: React.ReactNode; label: string; testId: string }) { return <button type="button" aria-pressed={checked} onClick={onChange} className={`flex min-h-10 w-full cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm font-bold transition-colors ${checked ? "border-[#c59b27] bg-[#fef8ea] text-[#684f0e]" : "border-slate-200 text-slate-500 dark:border-slate-700"}`} data-testid={testId}>{icon}{label}</button>; }
