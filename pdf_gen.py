"""
TechOps VPP Property Intelligence Report Generator
Styled to match Sentinel AI trial.pdf aesthetic:
  - Full dark background pages (#09111f)
  - Blue top header bar per page
  - Numbered section headings with accent color
  - Alternating-row tables with dark card background
  - Horizontal progress-bar charts
  - Matplotlib charts embedded as images
  - Footer with property address + page number
"""

import io
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfcanvas

# ─────────────────────────────────────────────
# PALETTE  (matches trial.pdf)
# ─────────────────────────────────────────────
BG          = colors.HexColor("#09111f")
CARD        = colors.HexColor("#101c2f")
CARD_ALT    = colors.HexColor("#0d1726")
HEADER_BAR  = colors.HexColor("#1a6bcc")   # blue top stripe
ACCENT      = colors.HexColor("#4da3ff")   # blue accent / section nums
ACCENT2     = colors.HexColor("#00c9a7")   # teal for positive values
WARN        = colors.HexColor("#f5a623")   # orange warning
DANGER      = colors.HexColor("#e74c3c")   # red
SUCCESS     = colors.HexColor("#2ecc71")   # green
TEXT        = colors.white
SUBTEXT     = colors.HexColor("#b7c9db")
BORDER      = colors.HexColor("#1e3a5f")
FOOTER_TEXT = colors.HexColor("#4a6fa5")

PAGE_W, PAGE_H = A4
MARGIN = 0.45 * inch
CONTENT_W = PAGE_W - 2 * MARGIN

# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────
def _style(name, **kw):
    base = kw.pop("parent", None)
    s = ParagraphStyle(name, **kw)
    return s

COVER_TITLE = _style("CoverTitle", fontSize=36, leading=44,
                     textColor=TEXT, alignment=TA_CENTER, spaceAfter=6,
                     fontName="Helvetica-Bold")

COVER_SUB = _style("CoverSub", fontSize=14, leading=20,
                   textColor=ACCENT, alignment=TA_CENTER, spaceAfter=4,
                   fontName="Helvetica")

COVER_BODY = _style("CoverBody", fontSize=10, leading=16,
                    textColor=SUBTEXT, alignment=TA_CENTER, spaceAfter=4,
                    fontName="Helvetica")

SEC_HEADING = _style("SecHeading", fontSize=18, leading=24,
                     textColor=TEXT, spaceAfter=10, spaceBefore=6,
                     fontName="Helvetica-Bold")

SUB_HEADING = _style("SubHeading", fontSize=11, leading=16,
                     textColor=ACCENT, spaceAfter=6, spaceBefore=4,
                     fontName="Helvetica-Bold")

BODY = _style("Body", fontSize=9.5, leading=15,
              textColor=TEXT, fontName="Helvetica")

BODY_SMALL = _style("BodySmall", fontSize=8.5, leading=13,
                    textColor=SUBTEXT, fontName="Helvetica")

METRIC_BIG = _style("MetricBig", fontSize=28, leading=34,
                    textColor=ACCENT, alignment=TA_CENTER,
                    fontName="Helvetica-Bold")

METRIC_LABEL = _style("MetricLabel", fontSize=8, leading=11,
                      textColor=SUBTEXT, alignment=TA_CENTER,
                      fontName="Helvetica")

TABLE_LABEL = _style("TableLabel", fontSize=8.5, leading=12,
                     textColor=SUBTEXT, fontName="Helvetica")

TABLE_VALUE = _style("TableValue", fontSize=8.5, leading=12,
                     textColor=TEXT, fontName="Helvetica")

CARD_TITLE = _style("CardTitle", fontSize=11, leading=15,
                    textColor=ACCENT, fontName="Helvetica-Bold", spaceAfter=4)

CARD_BODY = _style("CardBody", fontSize=9, leading=14,
                   textColor=TEXT, fontName="Helvetica")

PRIORITY_HIGH   = _style("PH", fontSize=8, textColor=DANGER,  fontName="Helvetica-Bold")
PRIORITY_MED    = _style("PM", fontSize=8, textColor=WARN,    fontName="Helvetica-Bold")
PRIORITY_LOW    = _style("PL", fontSize=8, textColor=SUCCESS, fontName="Helvetica-Bold")

# ─────────────────────────────────────────────
# PAGE TEMPLATE  (background + header + footer)
# ─────────────────────────────────────────────
class PageDecorator:
    def __init__(self, address="", total_pages=None):
        self.address = address
        self.total_pages = total_pages  # set after build if needed
        self._page_num = [0]

    def __call__(self, canv, doc):
        self._page_num[0] += 1
        pnum = self._page_num[0]
        w, h = A4

        # Full dark background
        canv.setFillColor(BG)
        canv.rect(0, 0, w, h, fill=1, stroke=0)

        # Top header bar
        canv.setFillColor(HEADER_BAR)
        canv.rect(0, h - 28, w, 28, fill=1, stroke=0)
        try:
            canv.drawImage("logo.png", MARGIN, h - 26, width=22, height=22,
                   preserveAspectRatio=True, mask="auto")
        except:
            pass
        canv.setFont("Helvetica-Bold", 7.5)
        canv.setFillColor(colors.white)
        canv.drawString(MARGIN, h - 18, "TECHOPS GLOBAL  —  AI VPP Property Intelligence Report")
        right_label = "Confidential — Authorized Recipients Only"
        canv.drawRightString(w - MARGIN, h - 18, right_label)

        # Bottom footer bar
        canv.setFillColor(FOOTER_TEXT)
        canv.setFont("Helvetica", 7)
        footer_y = 18
        canv.drawString(MARGIN, footer_y, f"Property: {self.address}")
        canv.drawRightString(w - MARGIN, footer_y, f"Page {pnum}")
        try:
            canv.drawImage("logo.png", w - MARGIN - 58, 6, width=36, height=26,
                   preserveAspectRatio=True, mask="auto")
        except:
            pass
        # Thin separator lines
        canv.setStrokeColor(BORDER)
        canv.setLineWidth(0.5)
        canv.line(MARGIN, h - 32, w - MARGIN, h - 32)
        canv.line(MARGIN, 28, w - MARGIN, 28)

# ─────────────────────────────────────────────
# HELPER FLOWABLES
# ─────────────────────────────────────────────
def hline(color=BORDER):
    return HRFlowable(width="100%", thickness=0.5, color=color, spaceAfter=8, spaceBefore=4)

def section_heading(num, title):
    txt = f'<font color="#4da3ff">{num}.</font>  {title}'
    return Paragraph(txt, SEC_HEADING)

def sub_heading(title):
    return Paragraph(title, SUB_HEADING)

def body_para(text):
    return Paragraph(text, BODY)

def kv_table(rows, col_widths=None):
    """Two-column label/value table with alternating rows."""
    if col_widths is None:
        col_widths = [CONTENT_W * 0.38, CONTENT_W * 0.62]
    data = [[Paragraph(k, TABLE_LABEL), Paragraph(v, TABLE_VALUE)] for k, v in rows]
    t = Table(data, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CARD, CARD_ALT]),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t

def analytics_card(title, content_para_or_text):
    """Dark card with accent border left like trial.pdf finding cards."""
    if isinstance(content_para_or_text, str):
        content = Paragraph(content_para_or_text, CARD_BODY)
    else:
        content = content_para_or_text
    inner = Table(
        [[Paragraph(title, CARD_TITLE)], [content]],
        colWidths=[CONTENT_W - 26]
    )
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    # Wrap in outer table to add left accent border
    outer = Table([[inner]], colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    return outer

def kpi_row(items):
    """Row of KPI boxes: items = list of (label, value, color)."""
    n = len(items)
    w = CONTENT_W / n - 4
    cells = []
    for label, value, col in items:
        cell = Table([
            [Paragraph(label, METRIC_LABEL)],
            [Paragraph(str(value), ParagraphStyle("mv", fontSize=22, leading=28,
                       textColor=col, alignment=TA_CENTER, fontName="Helvetica-Bold"))]
        ], colWidths=[w])
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CARD),
            ("BOX", (0, 0), (-1, -1), 0.5, col),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        cells.append(cell)
    row = Table([cells], colWidths=[w] * n, hAlign="CENTER")
    row.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row

# ─────────────────────────────────────────────
# MATPLOTLIB CHARTS  (saved to BytesIO → Image)
# ─────────────────────────────────────────────
DARK_BG = "#09111f"
CARD_C  = "#101c2f"
GRID_C  = "#1e3a5f"
BLUE    = "#4da3ff"
TEAL    = "#00c9a7"
ORANGE  = "#f5a623"
RED     = "#e74c3c"
GREEN   = "#2ecc71"

def _fig_to_image(fig, width_in, height_in):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=DARK_BG, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_in * inch, height=height_in * inch)


def chart_energy_mix(solar_pct=55, battery_pct=30, grid_pct=15):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3))
    fig.patch.set_facecolor(DARK_BG)

    # Donut chart
    sizes = [solar_pct, battery_pct, grid_pct]
    clrs  = [ORANGE, BLUE, GRID_C]
    labels= ["Solar", "Battery", "Grid Import"]
    wedges, texts, autotexts = ax1.pie(
        sizes, colors=clrs, autopct="%1.0f%%", startangle=90,
        pctdistance=0.75, wedgeprops=dict(width=0.5, edgecolor=DARK_BG, linewidth=2)
    )
    for at in autotexts:
        at.set_color("white"); at.set_fontsize(9)
    ax1.set_facecolor(DARK_BG)
    ax1.set_title("Energy Mix Distribution", color="white", fontsize=10, pad=10)
    ax1.legend(wedges, labels, loc="lower center", ncol=3,
               frameon=False, labelcolor="white", fontsize=8)

    # Monthly generation bar
    months = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
    # Simulate monthly based on solar irradiance variation
    base = 177302
    irr  = [0.85,0.90,1.05,1.10,1.12,1.10,1.08,1.10,1.05,0.95,0.85,0.82]
    vals = [base * f for f in irr]
    bar_colors = [BLUE if v >= base else TEAL for v in vals]
    bars = ax2.bar(months, [v/1000 for v in vals], color=bar_colors, edgecolor=DARK_BG, linewidth=0.5)
    ax2.set_facecolor(CARD_C)
    ax2.tick_params(colors="white", labelsize=7)
    for spine in ax2.spines.values():
        spine.set_edgecolor(GRID_C)
    ax2.yaxis.grid(True, color=GRID_C, linewidth=0.5, linestyle="--")
    ax2.set_axisbelow(True)
    ax2.set_title("Monthly Generation (MWh)", color="white", fontsize=10, pad=10)
    ax2.set_ylabel("MWh", color='#b7c9db', fontsize=8)
    # Add value on top of tallest
    for bar in bars:
        if bar.get_height() == max(b.get_height() for b in bars):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                     f"{bar.get_height():.0f}", ha="center", va="bottom",
                     color=ORANGE, fontsize=7, fontweight="bold")

    fig.tight_layout(pad=1.5)
    return _fig_to_image(fig, 7.2, 3.0)


def chart_financial_dcf(annual_savings, system_cost, roi_years):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3.2))
    fig.patch.set_facecolor(DARK_BG)

    # Cumulative cash flow (10-year)
    years = list(range(0, 11))
    cf = [-system_cost] + [annual_savings * y - system_cost for y in range(1, 11)]
    col = [RED if v < 0 else GREEN for v in cf]
    ax1.bar(years, [v/1000 for v in cf], color=col, edgecolor=DARK_BG, linewidth=0.5)
    ax1.axhline(0, color="white", linewidth=0.8, linestyle="-")
    ax1.axvline(roi_years, color=ORANGE, linewidth=1.2, linestyle="--", label=f"Payback ~{roi_years}yr")
    ax1.set_facecolor(CARD_C)
    ax1.tick_params(colors="white", labelsize=7)
    for spine in ax1.spines.values():
        spine.set_edgecolor(GRID_C)
    ax1.yaxis.grid(True, color=GRID_C, linewidth=0.4, linestyle="--")
    ax1.set_axisbelow(True)
    ax1.set_title("10-Year Cash Flow ($K)", color="white", fontsize=10, pad=10)
    ax1.set_xlabel("Year", color='#b7c9db', fontsize=8)
    ax1.set_ylabel("Cumulative ($K)", color='#b7c9db', fontsize=8)
    ax1.legend(frameon=False, labelcolor="white", fontsize=8)

    # Savings breakdown donut
    solar_s  = annual_savings * 0.65
    battery_s= annual_savings * 0.20
    vpp_s    = annual_savings * 0.15
    wedges, _, autotexts = ax2.pie(
        [solar_s, battery_s, vpp_s],
        colors=[ORANGE, BLUE, TEAL],
        autopct="%1.0f%%", startangle=90,
        pctdistance=0.75,
        wedgeprops=dict(width=0.5, edgecolor=DARK_BG, linewidth=2)
    )
    for at in autotexts:
        at.set_color("white"); at.set_fontsize(9)
    ax2.set_facecolor(DARK_BG)
    ax2.set_title("Annual Savings Breakdown", color="white", fontsize=10, pad=10)
    patches = [
        mpatches.Patch(color=ORANGE, label=f"Solar  ${solar_s:,.0f}"),
        mpatches.Patch(color=BLUE,   label=f"Battery  ${battery_s:,.0f}"),
        mpatches.Patch(color=TEAL,   label=f"VPP  ${vpp_s:,.0f}"),
    ]
    ax2.legend(handles=patches, loc="upper center",
           bbox_to_anchor=(0.5, -0.08),
           ncol=3, frameon=False,
           labelcolor="white", fontsize=7)

    fig.tight_layout(pad=1.5)
    fig.subplots_adjust(bottom=0.18)
    return _fig_to_image(fig, 7.2, 3.2)


def chart_vpp_radar(vpp_score):
    fig, ax = plt.subplots(figsize=(7.5, 3.2), subplot_kw=dict(projection="polar"))
    fig.patch.set_facecolor(DARK_BG)

    categories = ["Solar\nCapacity", "Battery\nReadiness", "Grid\nServices",
                  "Financial\nViability", "VPP\nScore"]
    N = len(categories)
    values = [
        min(100, vpp_score * 1.2),
        67,
        75,
        95,
        vpp_score,
    ]
    values += values[:1]
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    ax.set_facecolor(CARD_C)
    ax.plot(angles, values, color=BLUE, linewidth=2, linestyle="solid")
    ax.fill(angles, values, color=BLUE, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, color="white", size=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], color='#b7c9db', size=7)
    ax.grid(color=GRID_C, linewidth=0.5)
    ax.spines["polar"].set_color(GRID_C)
    ax.set_title("VPP Readiness Radar", color="white", fontsize=11, pad=15)

    fig.tight_layout(pad=1.0)
    return _fig_to_image(fig, 3.6, 3.2)


def chart_battery_dispatch():
    fig, ax = plt.subplots(figsize=(3.6, 3.2))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(CARD_C)

    hours = list(range(0, 24))
    # simulate 24h SOC profile
    soc = [40, 38, 36, 35, 34, 36, 42, 55, 65, 72, 78, 82,
           80, 75, 68, 60, 50, 45, 60, 75, 85, 70, 55, 45]
    ax.fill_between(hours, soc, alpha=0.3, color=TEAL)
    ax.plot(hours, soc, color=TEAL, linewidth=2)
    ax.axhline(80, color=ORANGE, linewidth=0.8, linestyle="--", label="Max SoC 80%")
    ax.axhline(20, color=RED, linewidth=0.8, linestyle="--", label="Min SoC 20%")
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.set_xticklabels(["00:00","06:00","12:00","18:00","23:00"], color="white", size=7)
    ax.tick_params(colors="white", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_C)
    ax.yaxis.grid(True, color=GRID_C, linewidth=0.4, linestyle="--")
    ax.set_axisbelow(True)
    ax.set_title("Battery State of Charge (24h)", color="white", fontsize=9, pad=8)
    ax.set_ylabel("SoC %", color='#b7c9db', fontsize=8)
    ax.set_xlabel("Hour", color='#b7c9db', fontsize=8)
    ax.legend(frameon=False, labelcolor="white", fontsize=7, loc="lower right")
    ax.set_ylim(0, 100)

    fig.tight_layout(pad=1.0)
    return _fig_to_image(fig, 3.6, 3.2)


def chart_category_scores(scores: dict):
    """Horizontal bar chart for category scores (like trial.pdf risk bars)."""
    fig, ax = plt.subplots(figsize=(5.5, 2.8))
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(CARD_C)

    labels = list(scores.keys())
    vals   = list(scores.values())
    y_pos  = range(len(labels))
    bar_colors = [GREEN if v >= 80 else BLUE if v >= 60 else ORANGE for v in vals]

    bars = ax.barh(list(y_pos), vals, color=bar_colors, height=0.5,
                   edgecolor=DARK_BG, linewidth=0.5)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f"{val}/100", va="center", ha="left", color="white", fontsize=8)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, color="white", fontsize=8)
    ax.set_xlim(0, 110)
    ax.set_xticks([])
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_C)
    ax.xaxis.grid(False)
    ax.set_title("Category Scores", color="white", fontsize=10, pad=8)

    fig.tight_layout(pad=1.0)
    return _fig_to_image(fig, 5.5, 2.8)


# ─────────────────────────────────────────────
# COVER PAGE HELPERS
# ─────────────────────────────────────────────
def cover_kpi_table(report):
    km = report["executive_summary"]["key_metrics"]
    items = [
        ("Solar Capacity",    f"{km['solar_capacity_kw']} kW",  ACCENT),
        ("Battery Storage",   f"{km['battery_mwh']} MWh",       TEAL),
        ("Annual Savings",    f"${km['annual_savings_usd']:,.0f}", SUCCESS),
        ("VPP Score",         f"{report['vpp_analysis']['vpp_score']}/100", WARN),
    ]
    return kpi_row(items)


# ─────────────────────────────────────────────
# MAIN REPORT BUILDER
# ─────────────────────────────────────────────
def generate_pdf_report(report, filename="TechOps_Report.pdf"):
    address = f"Lat {report['coordinates']['latitude']}, Lon {report['coordinates']['longitude']}"
    km   = report["executive_summary"]["key_metrics"]
    fin  = report["financial"]
    sol  = report["solar"]
    bat  = report["battery"]
    vpp  = report["vpp_analysis"]
    env  = report["environmental"]

    decorator = PageDecorator(address=address)

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=MARGIN + 30,
        bottomMargin=MARGIN + 20,
    )

    E = []   # elements

    # ══════════════════════════════════════════
    # PAGE 1 — COVER
    # ══════════════════════════════════════════
    E.append(Spacer(1, 10))
    try:
        logo = Image("logo.png", width=6*inch, height=2*inch)
        logo.hAlign = "CENTER"
        E.append(logo)
    except:
        pass
    E.append(Spacer(1, 16))
    E.append(Paragraph("TECHOPS GLOBAL", COVER_TITLE))
    E.append(Paragraph("AI VPP Property Intelligence Report", COVER_SUB))
    E.append(Spacer(1, 8))
    E.append(hline(ACCENT))
    E.append(Spacer(1, 10))
    E.append(Paragraph(report["executive_summary"]["summary"].strip(), COVER_BODY))
    E.append(Spacer(1, 28))

    # KPI row
    E.append(cover_kpi_table(report))
    E.append(Spacer(1, 20))

    # Property meta table
    prop = report["property"]
    E.append(kv_table([
        ("Property Type",      km["property_type"]),
        ("Roof Area",          f"{km['roof_area_sqm']:,.1f} sqm"),
        ("Coordinates",        f"{report['coordinates']['latitude']}°N, {report['coordinates']['longitude']}°E"),
        ("Annual Generation",  f"{km['annual_generation_kwh']:,.0f} kWh/year"),
        ("Est. Daily Load",    f"{prop['energy_profile']['estimated_daily_consumption_kwh']:,.1f} kWh/day"),
        ("Energy Intensity",   f"{prop['energy_profile']['energy_intensity']} kWh/sqm/year"),
    ]))
    E.append(Spacer(1, 30))

    # Confidential notice
    notice = Table(
        [[Paragraph(
            '<font color="#e74c3c">■</font>  '
            '<b><font color="#e74c3c">CONFIDENTIAL</font></b> — This report is intended exclusively '
            'for authorized recipients. Do not forward, copy, or distribute without written consent.',
            ParagraphStyle("note", fontSize=8, leading=12, textColor=TEXT,
                           fontName="Helvetica", alignment=TA_CENTER)
        )]],
        colWidths=[CONTENT_W]
    )
    notice.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD),
        ("BOX", (0, 0), (-1, -1), 0.5, DANGER),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
    ]))
    E.append(notice)
    E.append(PageBreak())

    # ══════════════════════════════════════════
    # PAGE 2 — EXECUTIVE SUMMARY + CATEGORY SCORES
    # ══════════════════════════════════════════
    E.append(section_heading("1", "Executive Summary"))
    E.append(hline())
    E.append(Spacer(1, 6))
    E.append(body_para(report["executive_summary"]["summary"].strip()))
    E.append(Spacer(1, 14))

    # Severity counts (like trial.pdf critical/high/med/low row)
    counts = [
        ("Solar Viability", sol["insights"]["solar_viability"],     ACCENT),
        ("Financial",       fin["insights"]["financial_viability"],  SUCCESS),
        ("Battery",         bat["insights"]["battery_readiness"],    TEAL),
        ("VPP Readiness",   vpp["readiness_level"],                  WARN),
        ("Env. Impact",     "High",                                  SUCCESS),
    ]
    count_cells = []
    for label, val, col in counts:
        cell_data = [
            [Paragraph(label, METRIC_LABEL)],
            [Paragraph(val, ParagraphStyle("cv", fontSize=11, leading=14,
                        textColor=col, alignment=TA_CENTER, fontName="Helvetica-Bold"))]
        ]
        cell = Table(cell_data, colWidths=[CONTENT_W / len(counts) - 3])
        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CARD),
            ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        count_cells.append(cell)
    row = Table([count_cells],
                colWidths=[CONTENT_W / len(counts) - 3] * len(counts))
    row.setStyle(TableStyle([
        ("LEFTPADDING", (0,0),(-1,-1), 2),
        ("RIGHTPADDING",(0,0),(-1,-1), 2),
    ]))
    E.append(row)
    E.append(Spacer(1, 14))

    # Category scores bar chart
    E.append(sub_heading("Category Score Breakdown"))
    scores_dict = {
        "Solar Generation":    92,
        "Financial Viability": 95,
        "Battery Readiness":   70,
        "VPP Integration":     int(vpp["vpp_score"]),
        "Environmental Impact":88,
        "Grid Services":       75,
    }
    E.append(chart_category_scores(scores_dict))
    E.append(Spacer(1, 14))

    # Environmental impact
    E.append(sub_heading("Environmental Impact"))
    E.append(kv_table([
        ("CO₂ Savings (Annual)", f"{env['impact']['carbon_savings_tons']:,.1f} metric tons"),
        ("Tree Equivalent",      f"{env['impact']['tree_equivalent']:,} trees planted"),
        ("Homes Powered",        f"{sol['equivalencies']['homes_powered']} homes/day"),
        ("EV Charges/Day",       f"{sol['equivalencies']['ev_charges']} sessions/day"),
    ]))
    E.append(PageBreak())

    # ══════════════════════════════════════════
    # PAGE 3 — SOLAR INTELLIGENCE
    # ══════════════════════════════════════════
    E.append(section_heading("2", "Solar Intelligence"))
    E.append(hline())
    E.append(Spacer(1, 8))

    E.append(kv_table([
        ("Usable Rooftop Area",  f"{int(km['roof_area_sqm'] * 0.80):,} sqm"),
        ("Panel Count (Est.)",   "2,208 panels"),
        ("System Capacity",      f"{km['solar_capacity_kw']:,.1f} kW"),
        ("Performance Ratio",    "0.80"),
        ("Peak Sun Hours",       f"{vpp['analysis']['peak_sun_hours']} hrs/day"),
        ("Specific Yield",       f"{sol['performance']['specific_yield']:,} kWh/kW/yr"),
        ("Capacity Factor",      f"{sol['performance']['capacity_factor']}%"),
        ("Solar Viability",      sol["insights"]["solar_viability"]),
    ]))
    E.append(Spacer(1, 12))

    E.append(sub_heading("Generation Profile"))
    E.append(kv_table([
        ("Daily Generation",    f"{int(km['annual_generation_kwh']/365):,} kWh/day"),
        ("Monthly Generation",  f"{int(km['annual_generation_kwh']/12):,} kWh/month"),
        ("Annual Generation",   f"{km['annual_generation_kwh']:,.0f} kWh/year"),
    ], col_widths=[CONTENT_W * 0.45, CONTENT_W * 0.55]))
    E.append(Spacer(1, 14))

    E.append(sub_heading("Energy Mix & Monthly Generation"))
    E.append(chart_energy_mix(55, 30, 15))
    E.append(Spacer(1, 12))

    E.append(analytics_card(
        "Strategic Solar Insights",
        sol["insights"]["strategic_summary"].strip()
    ))
    E.append(PageBreak())

    # ══════════════════════════════════════════
    # PAGE 4 — BATTERY INTELLIGENCE
    # ══════════════════════════════════════════
    E.append(section_heading("3", "Battery Intelligence"))
    E.append(hline())
    E.append(Spacer(1, 8))

    E.append(kv_table([
        ("Recommended Capacity",   f"{bat['storage']['battery_kwh']:,.0f} kWh"),
        ("Utility Scale",          f"{bat['storage']['battery_mwh']:.2f} MWh"),
        ("Strategy",               bat["storage"]["storage_summary"].split("\n")[0].strip()),
        ("Backup Duration",        f"{bat['performance']['estimated_backup_hours']} hours"),
        ("Dispatch Flexibility",   bat["performance"]["dispatch_capability"]),
        ("VPP Compatibility",      bat["insights"]["vpp_compatibility"]),
        ("Battery Readiness",      bat["insights"]["battery_readiness"]),
    ]))
    E.append(Spacer(1, 14))

    # Battery charts — side by side
    E.append(sub_heading("Battery Dispatch & VPP Radar"))
    bat_img  = chart_battery_dispatch()
    radar_img= chart_vpp_radar(vpp["vpp_score"])
    chart_row = Table([[bat_img, radar_img]],
                      colWidths=[CONTENT_W * 0.50, CONTENT_W * 0.50])
    chart_row.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
    ]))
    E.append(chart_row)
    E.append(Spacer(1, 12))

    # Applications
    E.append(sub_heading("Supported Grid Services"))
    services = bat["applications"]["supported_services"]
    service_rows = [[
        Paragraph(f'<font color="#4da3ff">▶</font>  {s}', BODY)
        for s in services
    ]]
    svc_t = Table(service_rows, colWidths=[CONTENT_W / len(services)] * len(services))
    svc_t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), CARD),
        ("BOX",        (0,0),(-1,-1), 0.4, BORDER),
        ("TOPPADDING", (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("ALIGN",      (0,0),(-1,-1), "CENTER"),
    ]))
    E.append(svc_t)
    E.append(Spacer(1, 12))

    E.append(analytics_card(
        "Strategic Battery Insights",
        bat["insights"]["strategic_summary"].strip()
    ))
    E.append(PageBreak())

    # ══════════════════════════════════════════
    # PAGE 5 — FINANCIAL INTELLIGENCE
    # ══════════════════════════════════════════
    E.append(section_heading("4", "Financial Intelligence"))
    E.append(hline())
    E.append(Spacer(1, 8))

    econ = fin["economics"]
    sav  = fin["savings"]
    E.append(kv_table([
        ("System Investment",   f"${econ['estimated_system_cost_usd']:,.0f} USD"),
        ("Annual Savings",      f"${econ['annual_savings_usd']:,.0f} USD/year"),
        ("Monthly Savings",     f"${sav['monthly_savings_usd']:,.0f} USD/month"),
        ("Daily Savings",       f"${sav['daily_savings_usd']:,.0f} USD/day"),
        ("Payback Period",      f"{econ['estimated_roi_years']} years"),
        ("Financial Viability", fin["insights"]["financial_viability"]),
        ("Investment Scale",    fin["insights"]["investment_scale"]),
    ]))
    E.append(Spacer(1, 14))

    E.append(sub_heading("10-Year Cash Flow & Savings Breakdown"))
    E.append(chart_financial_dcf(
        econ["annual_savings_usd"],
        econ["estimated_system_cost_usd"],
        econ["estimated_roi_years"]
    ))
    E.append(Spacer(1, 12))

    E.append(analytics_card(
        "Strategic Financial Insights",
        fin["insights"]["strategic_summary"].strip()
    ))
    E.append(PageBreak())

    # ══════════════════════════════════════════
    # PAGE 6 — VPP INTELLIGENCE
    # ══════════════════════════════════════════
    E.append(section_heading("5", "VPP Intelligence"))
    E.append(hline())
    E.append(Spacer(1, 8))

    # Big VPP score KPI
    score_val = vpp["vpp_score"]
    score_color = SUCCESS if score_val >= 80 else BLUE if score_val >= 60 else WARN
    score_items = [
        ("VPP SCORE",         f"{score_val}/100",                score_color),
        ("Readiness Level",   vpp["readiness_level"],             ACCENT),
        ("Solar Capacity",    f"{vpp['analysis']['solar_capacity_kw']} kW", ORANGE),
        ("Annual Generation", f"{vpp['analysis']['annual_generation_kwh']/1e6:.2f} GWh", TEAL),
    ]
    E.append(kpi_row(score_items))
    E.append(Spacer(1, 16))

    E.append(analytics_card("VPP Readiness Summary", vpp["summary"]))
    E.append(Spacer(1, 10))

    # Grid services
    
    E.append(sub_heading("Eligible Grid Services"))
    if services:
        service_rows = [[Paragraph(f'<font color="#4da3ff">▶</font>  {s}', BODY) for s in services]]
        svc_t = Table(service_rows, colWidths=[CONTENT_W / len(services)] * len(services))
        svc_t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), CARD),
        ("BOX",          (0,0),(-1,-1), 0.4, BORDER),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
    ]))
        E.append(svc_t)
        E.append(Spacer(1, 12))
    else:
        E.append(body_para("No specific grid services identified for this configuration."))
    # Strengths / Risks
    if vpp.get("strengths"):
        strengths_text = "<br/>".join(
            f'<font color="#2ecc71">▶</font>  {s}' for s in vpp["strengths"]
        )
        E.append(analytics_card("Key Strengths", strengths_text))
        E.append(Spacer(1, 10))

    if vpp.get("risks"):
        risks_text = "<br/>".join(
            f'<font color="#e74c3c">▶</font>  {r}' for r in vpp["risks"]
        )
        E.append(analytics_card("Potential Risks", risks_text))

    E.append(PageBreak())

    # ══════════════════════════════════════════
    # PAGE 7 — STRATEGIC ROADMAP
    # ══════════════════════════════════════════
    E.append(section_heading("6", "Strategic Roadmap"))
    E.append(hline())
    E.append(Spacer(1, 10))

    priority_hex = {"High": "#e74c3c", "Medium": "#f5a623", "Low": "#2ecc71"}
    priority_colors = {"High": DANGER, "Medium": WARN, "Low": SUCCESS}
    for i, rec in enumerate(report["recommendations"], 1):
        pcol = priority_colors.get(rec["priority"], ACCENT)
        phex = priority_hex.get(rec["priority"], "#4da3ff")
        priority_label = Paragraph(
            f'<font color="{phex}"><b>[{rec["priority"].upper()} PRIORITY]</b></font>  '
            f'{rec["recommendation"]}',
            ParagraphStyle("recbody", fontSize=9, leading=14, textColor=TEXT,
                           fontName="Helvetica")
        )
        inner = Table(
            [
                [Paragraph(f'{i}. {rec["title"]}', CARD_TITLE)],
                [priority_label],
            ],
            colWidths=[CONTENT_W - 26]
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND",     (0,0),(-1,-1), CARD),
            ("LEFTPADDING",    (0,0),(-1,-1), 14),
            ("RIGHTPADDING",   (0,0),(-1,-1), 14),
            ("TOPPADDING",     (0,0),(-1,-1), 10),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 10),
        ]))
        outer = Table([[inner]], colWidths=[CONTENT_W])
        outer.setStyle(TableStyle([
            ("BACKGROUND",  (0,0),(-1,-1), CARD),
            ("LEFTPADDING", (0,0),(-1,-1), 0),
            ("RIGHTPADDING",(0,0),(-1,-1), 0),
            ("TOPPADDING",  (0,0),(-1,-1), 0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ("LINEBEFORE",  (0,0),(0,-1),  3, pcol),
            ("BOX",         (0,0),(-1,-1), 0.4, BORDER),
        ]))
        E.append(KeepTogether([outer, Spacer(1, 12)]))

    # ─────────────────────────────────────────
    # BUILD
    # ─────────────────────────────────────────
    doc.build(
        E,
        onFirstPage=decorator,
        onLaterPages=decorator,
    )
    return filename


# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import json, sys

    sample_report = {
        "coordinates": {"latitude": 12.9716, "longitude": 77.5946},
        "executive_summary": {
            "summary": (
                "This property demonstrates strong distributed energy potential with an estimated "
                "rooftop area of 13805 sqm and regional solar irradiance of 6.0 Peak Sun Hours. "
                "The proposed solar system can generate approximately 5829 kWh/day, supporting "
                "commercial solar deployment, battery integration, and future Virtual Power Plant participation."
            ),
            "key_metrics": {
                "property_type": "Mall",
                "roof_area_sqm": 13804.57,
                "solar_capacity_kw": 1214.4,
                "battery_mwh": 1.75,
                "annual_generation_kwh": 2127628.8,
                "annual_savings_usd": 255315.46,
            },
        },
        "solar": {
            "technical": "Solar Infrastructure Analysis\n\n• Usable Rooftop Area: 11044 sqm\n• Estimated Panel Count: 2,208\n• Proposed System Capacity: 1214 kW\n• System Performance Ratio: 0.8",
            "generation": "Estimated Regional Solar Resource\n\n• Average Solar Irradiance: 6.0 PSH\n• Estimated Daily Generation: 5829 kWh/day\n• Annual Generation: 2127629 kWh/year",
            "equivalencies": {"homes_powered": 485, "ev_charges": 97, "equivalency_summary": ""},
            "performance": {"specific_yield": 1752, "capacity_factor": 20, "performance_summary": ""},
            "insights": {
                "solar_viability": "Excellent",
                "deployment_scale": "Commercial Scale",
                "strategic_summary": "The property demonstrates Excellent solar viability with a deployment classification of Commercial Scale. Based on estimated generation scale and rooftop utilization characteristics, the project appears suitable for future distributed energy integration including battery optimization and Virtual Power Plant participation.",
            },
        },
        "battery": {
            "storage": {"battery_kwh": 1748.74, "battery_mwh": 1.75,
                        "storage_summary": "Commercial Distributed Energy Storage\n\nBattery sized for commercial optimization."},
            "applications": {
                "supported_services": ["Peak Shaving", "Demand Response", "Backup Power", "Energy Arbitrage"],
                "applications_summary": "",
            },
            "performance": {"estimated_backup_hours": 3.5, "dispatch_capability": "Moderate", "performance_summary": ""},
            "insights": {
                "battery_readiness": "Commercial Ready",
                "vpp_compatibility": "Moderate",
                "strategic_summary": "The battery system architecture appears suitable for future energy optimization strategies including distributed storage coordination, demand response participation, and Virtual Power Plant integration.",
            },
        },
        "financial": {
            "economics": {
                "estimated_system_cost_usd": 971520,
                "annual_savings_usd": 255315.46,
                "estimated_roi_years": 3.8,
                "economics_summary": "",
            },
            "savings": {"monthly_savings_usd": 21276.29, "daily_savings_usd": 699.49, "savings_summary": ""},
            "insights": {
                "financial_viability": "Excellent",
                "investment_scale": "Commercial Scale",
                "strategic_summary": "The proposed distributed energy investment demonstrates strong potential for long-term operational savings while supporting future energy resiliency and sustainability objectives.",
            },
        },
        "property": {
            "classification": {"property_type": "Mall", "roof_area_sqm": 13804.57},
            "energy_profile": {
                "estimated_daily_consumption_kwh": 8282.74,
                "estimated_monthly_consumption_kwh": 248482.26,
                "energy_intensity": 18,
            },
            "insights": {"consumption_methodology": "Estimated using commercial energy benchmarks.", "property_comment": ""},
        },
        "environmental": {
            "impact": {"carbon_savings_tons": 1489.34, "tree_equivalent": 67020},
            "insights": {"environment_comment": ""},
        },
        "vpp_analysis": {
            "vpp_score": 67,
            "readiness_level": "Moderate",
            "summary": "The property has moderate VPP potential with opportunities for optimization.",
            "strengths": [
                "Strong commercial solar generation potential.",
                "Excellent regional solar irradiance.",
                "Commercial property profile aligns well with distributed energy deployment.",
            ],
            "risks": [],
            "recommendations": [],
            "grid_services": ["Peak Shaving", "Demand Response", "Backup Power", "Grid Export Support"],
            "analysis": {
                "solar_capacity_kw": 1214.4,
                "battery_mwh": 1.75,
                "peak_sun_hours": 6,
                "annual_generation_kwh": 2127628.8,
            },
        },
        "recommendations": [
            {
                "category": "VPP Integration",
                "priority": "High",
                "title": "Evaluate VPP Participation",
                "recommendation": "The property's operational and energy characteristics appear well-suited for future Virtual Power Plant integration. Participation in distributed energy aggregation programs may unlock additional value streams through demand response, grid support services, and energy market participation.",
            },
            {
                "category": "Sustainability",
                "priority": "Low",
                "title": "Leverage Sustainability Benefits",
                "recommendation": "The projected carbon reduction potential may contribute meaningfully toward corporate ESG initiatives and sustainability targets. The organization may benefit from incorporating this project into broader environmental reporting and decarbonization strategies.",
            },
        ],
    }

    out = generate_pdf_report(sample_report)
    print(f"Generated: {out}")