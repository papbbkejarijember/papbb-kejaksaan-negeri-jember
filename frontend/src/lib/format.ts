export function formatRupiah(value: number | null | undefined) {
  if (value === null || value === undefined) return "Belum ada penawaran";
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function statusLabel(status: "upcoming" | "ongoing" | "ended") {
  return { upcoming: "Akan Datang", ongoing: "Berlangsung", ended: "Selesai" }[status];
}
