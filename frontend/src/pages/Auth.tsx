import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, KeyRound, LockKeyhole, Mail, ShieldCheck, UserPlus, UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiPost, ApiError } from "@/lib/api";
import type { SessionResponse } from "@/lib/types";

function errorMessage(error: unknown) {
  if (error instanceof ApiError && typeof error.body === "object" && error.body && "detail" in error.body) return String(error.body.detail);
  return "Terjadi kendala. Silakan coba kembali.";
}

export default function Auth() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [legalConsent, setLegalConsent] = useState(false);
  const mutation = useMutation({
    mutationFn: () => mode === "login" ? apiPost<SessionResponse>("/auth/login", { email, password }) : apiPost<SessionResponse>("/auth/register", { full_name: fullName, email, phone: phone || null, password, legal_consent: legalConsent }),
    onSuccess: async ({ user }) => {
      await queryClient.invalidateQueries({ queryKey: ["current-user"] });
      toast.success(mode === "login" ? "Selamat datang kembali." : "Akun peserta berhasil dibuat.");
      navigate(user.role === "admin" ? "/admin" : "/dashboard");
    },
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate();
  };

  return (
    <AppShell>
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8 lg:py-20">
        <section className="max-w-xl" data-testid="auth-intro-section">
          <Link to="/" className="mb-8 inline-flex items-center gap-2 text-sm font-bold text-[#0f2c59] hover:text-[#c59b27] dark:text-[#f8e7aa]" data-testid="auth-back-link"><ArrowLeft size={16} />Kembali ke katalog</Link>
          <div className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-[#eff4fb] text-[#0f2c59] dark:bg-slate-800 dark:text-[#f8e7aa]"><ShieldCheck size={28} /></div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#c59b27]" data-testid="auth-kicker">Akses portal lelang</p>
          <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-[#0f2c59] sm:text-5xl dark:text-white" data-testid="auth-page-title">Kelola partisipasi lelang Anda dengan aman.</h1>
          <p className="mt-5 max-w-lg leading-relaxed text-slate-600 dark:text-slate-300" data-testid="auth-page-description">Peserta dapat mengikuti lelang, melihat riwayat penawaran, dan menerima pemberitahuan status melalui satu akun terverifikasi.</p>
          <div className="mt-8 space-y-3 text-sm font-semibold text-slate-700 dark:text-slate-200"><div className="flex items-center gap-3" data-testid="auth-benefit-verification"><span className="grid h-8 w-8 place-items-center rounded-lg bg-[#fef8ea] text-[#c59b27]"><ShieldCheck size={16} /></span>Identitas sensitif dienkripsi dan aktivitas tercatat</div><div className="flex items-center gap-3" data-testid="auth-benefit-notification"><span className="grid h-8 w-8 place-items-center rounded-lg bg-[#fef8ea] text-[#c59b27]"><Mail size={16} /></span>Notifikasi email transaksional melalui Brevo</div></div>
        </section>

        <Card className="mx-auto w-full max-w-xl border-slate-200 shadow-xl shadow-[#0f2c59]/5 dark:border-slate-700 dark:bg-slate-900" data-testid="auth-card">
          <CardHeader className="space-y-4 border-b border-slate-100 dark:border-slate-700"><div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800"><button type="button" onClick={() => { setMode("login"); mutation.reset(); }} className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-bold transition-colors ${mode === "login" ? "bg-white text-[#0f2c59] shadow-sm dark:bg-slate-700 dark:text-white" : "text-slate-500"}`} data-testid="auth-login-tab"><KeyRound size={15} className="mr-2 inline" />Masuk</button><button type="button" onClick={() => { setMode("register"); mutation.reset(); }} className={`flex-1 rounded-lg px-4 py-2.5 text-sm font-bold transition-colors ${mode === "register" ? "bg-white text-[#0f2c59] shadow-sm dark:bg-slate-700 dark:text-white" : "text-slate-500"}`} data-testid="auth-register-tab"><UserPlus size={15} className="mr-2 inline" />Daftar peserta</button></div><CardTitle className="text-xl text-[#0f2c59] dark:text-white" data-testid="auth-card-title">{mode === "login" ? "Masuk ke akun Anda" : "Buat akun peserta"}</CardTitle></CardHeader>
          <CardContent className="p-6 sm:p-8">
            <form onSubmit={submit} className="space-y-5" data-testid="auth-form">
              {mode === "register" && <div className="space-y-2"><Label htmlFor="auth-full-name">Nama lengkap</Label><div className="relative"><UserRound className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} /><Input id="auth-full-name" value={fullName} onChange={(event) => setFullName(event.target.value)} className="pl-10" placeholder="Nama sesuai identitas" required data-testid="auth-full-name-input" /></div></div>}
              <div className="space-y-2"><Label htmlFor="auth-email">Email</Label><div className="relative"><Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} /><Input id="auth-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="pl-10" placeholder="nama@email.com" required data-testid="auth-email-input" /></div></div>
              {mode === "register" && <div className="space-y-2"><Label htmlFor="auth-phone">Nomor telepon <span className="font-normal text-slate-400">(opsional)</span></Label><Input id="auth-phone" value={phone} onChange={(event) => setPhone(event.target.value)} placeholder="62812…" data-testid="auth-phone-input" /></div>}
              <div className="space-y-2"><Label htmlFor="auth-password">Kata sandi</Label><div className="relative"><LockKeyhole className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} /><Input id="auth-password" type="password" minLength={mode === "register" ? 12 : 8} value={password} onChange={(event) => setPassword(event.target.value)} className="pl-10" placeholder={mode === "register" ? "12+ karakter, besar/kecil, angka, simbol" : "Kata sandi akun"} required data-testid="auth-password-input" /></div></div>
              {mode === "register" && <label className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 text-xs leading-relaxed text-slate-600 dark:border-slate-700 dark:text-slate-300" data-testid="legal-consent-label"><input type="checkbox" checked={legalConsent} onChange={(event) => setLegalConsent(event.target.checked)} required className="mt-0.5" data-testid="legal-consent-checkbox" /><span>Saya menyetujui <Link to="/legal#privacy" className="font-bold text-[#0f2c59] underline dark:text-[#f8e7aa]">Kebijakan Privasi</Link> dan <Link to="/legal#terms" className="font-bold text-[#0f2c59] underline dark:text-[#f8e7aa]">Syarat Layanan</Link>.</span></label>}
              {mutation.isError && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" data-testid="auth-error-message">{errorMessage(mutation.error)}</p>}
              <Button type="submit" className="h-11 w-full gap-2 bg-[#0f2c59] font-bold hover:bg-[#163b72]" disabled={mutation.isPending || (mode === "register" && !legalConsent)} data-testid="auth-submit-button">{mutation.isPending ? "Memproses…" : mode === "login" ? "Masuk ke portal" : "Daftar sebagai peserta"}</Button>
            </form>
            <div className="mt-7 rounded-xl border border-[#e5c158] bg-[#fef8ea] p-4 text-xs leading-relaxed text-[#684f0e]" data-testid="production-access-note"><p className="font-bold">Akses terlindungi</p><p className="mt-1">Akun petugas tidak dipublikasikan. Lima kegagalan login akan membatasi percobaan selama 15 menit.</p></div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
