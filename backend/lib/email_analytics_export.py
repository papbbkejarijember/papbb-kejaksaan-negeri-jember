import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO

import httpx
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.notification import EmailAnalytics


LOGO_URL = "https://customer-assets-7cd3h4nn.emergentagent.net/job_auction-live-17/artifacts/jmc80t8v_LOGO_PAPBB_JEMBER.png"
NAVY = colors.HexColor("#0F2C59")
GOLD = colors.HexColor("#C59B27")
GREEN = colors.HexColor("#059669")
RED = colors.HexColor("#EF4444")
SLATE = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")


def period_label(value: str) -> str:
    return {"7d": "7 Hari Terakhir", "30d": "30 Hari Terakhir", "all": "Sepanjang Waktu"}[value]


def build_analytics_csv(analytics: EmailAnalytics) -> bytes:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["LAPORAN ANALITIK EMAIL - KEJAKSAAN NEGERI JEMBER"])
    writer.writerow(["Periode", period_label(analytics.range)])
    writer.writerow(["Rentang tanggal", f"{analytics.from_date or '-'} s.d. {analytics.to_date}"])
    writer.writerow(["Dibuat", datetime.now(timezone.utc).isoformat()])
    writer.writerow([])
    writer.writerow(["RINGKASAN KPI", "Nilai"])
    writer.writerow(["Email diproses", analytics.totals.sent])
    writer.writerow(["Email terkirim", analytics.totals.delivered])
    writer.writerow(["Rasio terkirim", f"{analytics.delivery_rate}%"])
    writer.writerow(["Email dibuka", analytics.totals.opened])
    writer.writerow(["Rasio dibuka", f"{analytics.open_rate}%"])
    writer.writerow(["Email gagal", analytics.totals.failed])
    writer.writerow(["Rasio gagal", f"{analytics.failure_rate}%"])
    writer.writerow([])
    writer.writerow(["TREN HARIAN"])
    writer.writerow(["Tanggal", "Diproses", "Terkirim", "Dibuka", "Gagal"])
    for point in analytics.trend:
        writer.writerow([point.date, point.sent, point.delivered, point.opened, point.failed])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


async def _fetch_logo() -> BytesIO | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(LOGO_URL)
            response.raise_for_status()
        return BytesIO(response.content)
    except httpx.HTTPError:
        return None


def _trend_chart(analytics: EmailAnalytics) -> Drawing:
    drawing = Drawing(720, 235)
    chart = HorizontalLineChart()
    chart.x = 45
    chart.y = 40
    chart.height = 150
    chart.width = 630
    points = analytics.trend or []
    chart.data = [
        [point.sent for point in points],
        [point.delivered for point in points],
        [point.opened for point in points],
        [point.failed for point in points],
    ]
    chart.categoryAxis.categoryNames = [point.date[5:] for point in points]
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.angle = 45 if len(points) > 12 else 0
    chart.categoryAxis.labels.dy = -12 if len(points) > 12 else -6
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(1, max((point.sent for point in points), default=1))
    chart.valueAxis.valueStep = max(1, int(chart.valueAxis.valueMax / 5) or 1)
    chart.valueAxis.labels.fontSize = 8
    chart.lines[0].strokeColor = NAVY
    chart.lines[1].strokeColor = GREEN
    chart.lines[2].strokeColor = GOLD
    chart.lines[3].strokeColor = RED
    for index in range(4):
        chart.lines[index].strokeWidth = 2
    drawing.add(chart)
    legend = Legend()
    legend.x = 250
    legend.y = 215
    legend.fontSize = 8
    legend.dx = 8
    legend.dy = 8
    legend.deltax = 85
    legend.columnMaximum = 1
    legend.colorNamePairs = [(NAVY, "Diproses"), (GREEN, "Terkirim"), (GOLD, "Dibuka"), (RED, "Gagal")]
    drawing.add(legend)
    return drawing


async def build_analytics_pdf(analytics: EmailAnalytics) -> bytes:
    buffer = BytesIO()
    page_width, _ = landscape(A4)
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=15 * mm,
        title="Laporan Analitik Email Kejaksaan Negeri Jember",
        author="Portal Lelang Kejaksaan Negeri Jember",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=NAVY, spaceAfter=4))
    styles.add(ParagraphStyle(name="SmallCenter", parent=styles["BodyText"], fontSize=8, leading=10, textColor=SLATE, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=NAVY, spaceBefore=8, spaceAfter=7))
    story = []
    logo_data = await _fetch_logo()
    logo = Image(logo_data, width=24 * mm, height=24 * mm) if logo_data else Paragraph("<b>BPA</b>", styles["Title"])
    header_text = Paragraph(
        "<b>KEJAKSAAN NEGERI JEMBER</b><br/><font size='13'>LAPORAN ANALITIK EMAIL TRANSAKSIONAL</font><br/>"
        f"<font size='9' color='#64748B'>{period_label(analytics.range)} · {analytics.from_date or '-'} s.d. {analytics.to_date}</font>",
        styles["ReportTitle"],
    )
    header = Table([[logo, header_text]], colWidths=[30 * mm, page_width - 72 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 1.5, GOLD), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([header, Spacer(1, 7 * mm)])

    kpis = [
        ("EMAIL DIPROSES", str(analytics.totals.sent), "Total email Brevo"),
        ("RASIO TERKIRIM", f"{analytics.delivery_rate}%", f"{analytics.totals.delivered} email"),
        ("RASIO DIBUKA", f"{analytics.open_rate}%", f"{analytics.totals.opened} email"),
        ("RASIO GAGAL", f"{analytics.failure_rate}%", f"{analytics.totals.failed} email"),
    ]
    kpi_cells = [Paragraph(f"<font size='8' color='#64748B'>{label}</font><br/><font size='20' color='#0F2C59'><b>{value}</b></font><br/><font size='8' color='#94A3B8'>{helper}</font>", styles["BodyText"]) for label, value, helper in kpis]
    kpi_table = Table([kpi_cells], colWidths=[(page_width - 32 * mm) / 4] * 4)
    kpi_table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")), ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("PADDING", (0, 0), (-1, -1), 10)]))
    story.extend([kpi_table, Spacer(1, 5 * mm)])

    story.append(Paragraph("Funnel Status Pengiriman", styles["Section"]))
    funnel_rows = [
        ["Diproses", analytics.totals.sent, "100%" if analytics.totals.sent else "0%"],
        ["Terkirim", analytics.totals.delivered, f"{analytics.delivery_rate}%"],
        ["Dibuka", analytics.totals.opened, f"{analytics.open_rate}% dari terkirim"],
        ["Gagal", analytics.totals.failed, f"{analytics.failure_rate}%"],
    ]
    funnel = Table([["Status", "Jumlah", "Rasio"], *funnel_rows], colWidths=[80 * mm, 35 * mm, 55 * mm])
    funnel.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("PADDING", (0, 0), (-1, -1), 6)]))
    story.extend([funnel, Spacer(1, 4 * mm), Paragraph("Grafik Tren Harian", styles["Section"]), _trend_chart(analytics)])

    story.append(Paragraph("Rincian Tren Harian", styles["Section"]))
    trend_rows = [["Tanggal", "Diproses", "Terkirim", "Dibuka", "Gagal"]] + [[point.date, point.sent, point.delivered, point.opened, point.failed] for point in analytics.trend]
    trend_table = Table(trend_rows, repeatRows=1, colWidths=[48 * mm, 34 * mm, 34 * mm, 34 * mm, 34 * mm])
    trend_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]), ("FONTSIZE", (0, 0), (-1, -1), 8), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.extend([trend_table, Spacer(1, 12 * mm)])
    signature = Table(
        [[Paragraph("Mengetahui,<br/><b>Kepala Kejaksaan Negeri Jember</b><br/><br/><br/><br/>(____________________________)", styles["SmallCenter"]), Paragraph("Jember, __________________<br/><b>Petugas Pengelola</b><br/><br/><br/><br/>(____________________________)", styles["SmallCenter"]) ]],
        colWidths=[85 * mm, 85 * mm],
    )
    signature.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(signature)

    def page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(SLATE)
        canvas.drawString(16 * mm, 8 * mm, f"Dicetak {datetime.now(timezone.utc).strftime('%d-%m-%Y %H:%M UTC')} · Portal Lelang Kejaksaan Negeri Jember")
        canvas.drawRightString(page_width - 16 * mm, 8 * mm, f"Halaman {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return buffer.getvalue()