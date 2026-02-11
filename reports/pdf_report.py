"""
Professional PDF report generator for ON24 GEO Benchmark results.
Uses reportlab for PDF layout and matplotlib for charts.
"""

import io
import os
import json
import tempfile
from datetime import datetime
from itertools import groupby
from operator import itemgetter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

from db.database import DatabaseManager
from analysis.recommendations import RecommendationEngine


# ── Brand colors ──────────────────────────────────────────────
BRAND_COLORS = {
    "on24": "#0066CC",
    "goldcast": "#E8712B",
    "zoom": "#2D8CFF",
}
BRAND_DISPLAY = {"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"}
ENGINE_DISPLAY = {
    "grok_web_search": "Grok (Web Search)",
    "chatgpt_web_search": "ChatGPT (Web Search)",
    "claude_parametric": "Claude (Parametric)",
}
CATEGORY_DISPLAY = {
    "platform_comparison": "Platform Comparison",
    "use_case": "Use Case",
    "feature": "Feature",
    "roi_strategy": "ROI / Strategy",
    "technical": "Technical",
}

# ── Color palette ─────────────────────────────────────────────
ON24_BLUE = colors.HexColor("#0066CC")
ON24_DARK = colors.HexColor("#003366")
GOLD = colors.HexColor("#E8712B")
ZOOM_BLUE = colors.HexColor("#2D8CFF")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MED_GRAY = colors.HexColor("#CCCCCC")
DARK_GRAY = colors.HexColor("#333333")
GREEN = colors.HexColor("#27AE60")
RED = colors.HexColor("#E74C3C")
AMBER = colors.HexColor("#F39C12")


class GEOReportGenerator:
    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Add custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            "ReportTitle", parent=self.styles["Title"],
            fontSize=28, textColor=ON24_DARK, spaceAfter=6,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            "ReportSubtitle", parent=self.styles["Normal"],
            fontSize=14, textColor=colors.HexColor("#666666"),
            spaceAfter=20, alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            "SectionHeader", parent=self.styles["Heading1"],
            fontSize=20, textColor=ON24_DARK, spaceBefore=18,
            spaceAfter=10, fontName="Helvetica-Bold",
            borderWidth=0, borderPadding=0,
        ))
        self.styles.add(ParagraphStyle(
            "SubHeader", parent=self.styles["Heading2"],
            fontSize=14, textColor=ON24_BLUE, spaceBefore=12,
            spaceAfter=6, fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            "BodyText", parent=self.styles["Normal"],
            fontSize=10, leading=14, spaceAfter=8,
            alignment=TA_JUSTIFY, textColor=DARK_GRAY,
        ))
        self.styles.add(ParagraphStyle(
            "SmallText", parent=self.styles["Normal"],
            fontSize=8, leading=10, textColor=colors.HexColor("#888888"),
        ))
        self.styles.add(ParagraphStyle(
            "KPILabel", parent=self.styles["Normal"],
            fontSize=9, textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            "KPIValue", parent=self.styles["Normal"],
            fontSize=22, fontName="Helvetica-Bold",
            textColor=ON24_DARK, alignment=TA_CENTER, spaceAfter=2,
        ))
        self.styles.add(ParagraphStyle(
            "Winner", parent=self.styles["Normal"],
            fontSize=10, textColor=GREEN, fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            "Loser", parent=self.styles["Normal"],
            fontSize=10, textColor=RED, fontName="Helvetica-Bold",
        ))
        self.styles.add(ParagraphStyle(
            "BulletItem", parent=self.styles["Normal"],
            fontSize=10, leading=14, leftIndent=20, spaceBefore=2,
            spaceAfter=2, bulletIndent=8, textColor=DARK_GRAY,
        ))
        self.styles.add(ParagraphStyle(
            "FooterStyle", parent=self.styles["Normal"],
            fontSize=8, textColor=colors.HexColor("#AAAAAA"),
            alignment=TA_CENTER,
        ))

    # ── Data loading ──────────────────────────────────────────
    def _load_data(self, run_id=None):
        """Load all benchmark data for a run."""
        if run_id is None:
            run_id = self.db.get_latest_run_id()
        if not run_id:
            raise ValueError("No completed benchmark run found.")

        run = self.db.get_run(run_id)
        metrics = self.db.get_daily_metrics_for_run(run_id)
        queries = {q["id"]: q for q in self.db.get_active_queries()}

        # Aggregate SOV per engine per brand
        engines = sorted(set(m["llm_engine"] for m in metrics))
        brands = ["on24", "goldcast", "zoom"]

        sov_by_engine = {}
        pos_by_engine = {}
        sent_by_engine = {}
        win_by_engine = {}

        for engine in engines:
            eng_metrics = [m for m in metrics if m["llm_engine"] == engine]
            sov_by_engine[engine] = {}
            pos_by_engine[engine] = {}
            sent_by_engine[engine] = {}
            win_by_engine[engine] = {}
            for brand in brands:
                bm = [m for m in eng_metrics if m["brand"] == brand]
                if bm:
                    sov_by_engine[engine][brand] = sum(m["is_mentioned"] for m in bm) / len(bm) * 100
                    positions = [m["first_mention_position"] for m in bm if m["first_mention_position"]]
                    pos_by_engine[engine][brand] = sum(positions) / len(positions) if positions else None
                    sentiments = [m["avg_sentiment_score"] for m in bm if m["avg_sentiment_score"] is not None]
                    sent_by_engine[engine][brand] = sum(sentiments) / len(sentiments) if sentiments else 0
                    win_by_engine[engine][brand] = sum(m["is_winner"] for m in bm) / len(bm) * 100

        # Category breakdown
        cat_data = {}
        for engine in engines:
            eng_metrics = [m for m in metrics if m["llm_engine"] == engine]
            sorted_m = sorted(eng_metrics, key=itemgetter("query_category"))
            for cat, group in groupby(sorted_m, key=itemgetter("query_category")):
                rows = list(group)
                if cat not in cat_data:
                    cat_data[cat] = {}
                if engine not in cat_data[cat]:
                    cat_data[cat][engine] = {}
                for brand in brands:
                    bm = [r for r in rows if r["brand"] == brand]
                    if bm:
                        cat_data[cat][engine][brand] = {
                            "sov": sum(r["is_mentioned"] for r in bm) / len(bm) * 100,
                            "wins": sum(r["is_winner"] for r in bm),
                            "total": len(bm),
                        }

        # Per-query winners
        query_winners = {}
        for engine in engines:
            eng_metrics = [m for m in metrics if m["llm_engine"] == engine]
            sorted_m = sorted(eng_metrics, key=itemgetter("query_id"))
            for qid, group in groupby(sorted_m, key=itemgetter("query_id")):
                rows = list(group)
                winner = next((r for r in rows if r["is_winner"]), None)
                if qid not in query_winners:
                    query_winners[qid] = {}
                query_winners[qid][engine] = {
                    "winner": winner["brand"] if winner else None,
                    "brands": {r["brand"]: {
                        "mentioned": r["is_mentioned"],
                        "position": r["first_mention_position"],
                        "sentiment": r["avg_sentiment_score"],
                        "primary": r["is_primary_recommendation"],
                    } for r in rows},
                }

        # Citations
        citations = self.db.query(
            "SELECT * FROM citations WHERE run_id = ?", (run_id,)
        )
        citation_summary = {"on24_www": 0, "on24_event": 0, "goldcast": 0, "zoom": 0, "other": 0}
        for c in citations:
            if c["is_on24_www"]:
                citation_summary["on24_www"] += 1
            elif c["is_on24_event"]:
                citation_summary["on24_event"] += 1
            elif c["brand_association"] == "goldcast":
                citation_summary["goldcast"] += 1
            elif c["brand_association"] == "zoom":
                citation_summary["zoom"] += 1
            else:
                citation_summary["other"] += 1

        return {
            "run": run,
            "run_id": run_id,
            "metrics": metrics,
            "queries": queries,
            "engines": engines,
            "brands": brands,
            "sov": sov_by_engine,
            "positions": pos_by_engine,
            "sentiment": sent_by_engine,
            "win_rate": win_by_engine,
            "cat_data": cat_data,
            "query_winners": query_winners,
            "citations": citation_summary,
            "total_citations": len(citations),
        }

    # ── Chart generators (matplotlib → PNG → reportlab Image) ─
    def _make_chart_image(self, fig, width=6.5, height=3.5):
        """Convert a matplotlib figure to a reportlab Image flowable."""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        img = Image(buf, width=width * inch, height=height * inch)
        return img

    def _chart_sov_comparison(self, data):
        """Grouped bar chart: SOV by brand across engines."""
        fig, ax = plt.subplots(figsize=(8, 4))
        engines = data["engines"]
        brands = data["brands"]
        x = np.arange(len(engines))
        width = 0.22

        for i, brand in enumerate(brands):
            vals = [data["sov"].get(e, {}).get(brand, 0) for e in engines]
            bars = ax.bar(x + i * width, vals, width, label=BRAND_DISPLAY[brand],
                         color=BRAND_COLORS[brand], edgecolor="white", linewidth=0.5)
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f"{val:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

        ax.set_ylabel("Share of Voice (%)", fontsize=10)
        ax.set_title("Share of Voice by LLM Engine", fontsize=13, fontweight="bold", pad=12)
        ax.set_xticks(x + width)
        ax.set_xticklabels([ENGINE_DISPLAY.get(e, e) for e in engines], fontsize=9)
        ax.set_ylim(0, 110)
        ax.legend(fontsize=9, loc="upper right")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        return self._make_chart_image(fig, width=6.5, height=3.5)

    def _chart_win_rate(self, data):
        """Grouped bar chart: Win Rate by brand across engines."""
        fig, ax = plt.subplots(figsize=(8, 4))
        engines = data["engines"]
        brands = data["brands"]
        x = np.arange(len(engines))
        width = 0.22

        for i, brand in enumerate(brands):
            vals = [data["win_rate"].get(e, {}).get(brand, 0) for e in engines]
            bars = ax.bar(x + i * width, vals, width, label=BRAND_DISPLAY[brand],
                         color=BRAND_COLORS[brand], edgecolor="white", linewidth=0.5)
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f"{val:.0f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

        ax.set_ylabel("Win Rate (%)", fontsize=10)
        ax.set_title("Win Rate by LLM Engine", fontsize=13, fontweight="bold", pad=12)
        ax.set_xticks(x + width)
        ax.set_xticklabels([ENGINE_DISPLAY.get(e, e) for e in engines], fontsize=9)
        ax.set_ylim(0, max(max(data["win_rate"].get(e, {}).get(b, 0) for e in engines for b in brands), 10) + 15)
        ax.legend(fontsize=9, loc="upper right")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        return self._make_chart_image(fig, width=6.5, height=3.5)

    def _chart_sentiment(self, data):
        """Horizontal bar chart: Average sentiment by brand across engines."""
        fig, ax = plt.subplots(figsize=(8, 4))
        engines = data["engines"]
        brands = data["brands"]
        y = np.arange(len(engines))
        height = 0.22

        for i, brand in enumerate(brands):
            vals = [data["sentiment"].get(e, {}).get(brand, 0) for e in engines]
            bars = ax.barh(y + i * height, vals, height, label=BRAND_DISPLAY[brand],
                          color=BRAND_COLORS[brand], edgecolor="white", linewidth=0.5)
            for bar, val in zip(bars, vals):
                offset = 0.02 if val >= 0 else -0.02
                ha = "left" if val >= 0 else "right"
                ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                        f"{val:.2f}", ha=ha, va="center", fontsize=8, fontweight="bold")

        ax.set_xlabel("Avg Sentiment Score (-1.0 to 1.0)", fontsize=10)
        ax.set_title("Sentiment Analysis by LLM Engine", fontsize=13, fontweight="bold", pad=12)
        ax.set_yticks(y + height)
        ax.set_yticklabels([ENGINE_DISPLAY.get(e, e) for e in engines], fontsize=9)
        ax.axvline(x=0, color="gray", linewidth=0.5, linestyle="--")
        ax.set_xlim(-1.0, 1.0)
        ax.legend(fontsize=9, loc="lower right")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        return self._make_chart_image(fig, width=6.5, height=3.5)

    def _chart_position(self, data):
        """Bar chart: Average mention position (lower is better)."""
        fig, ax = plt.subplots(figsize=(8, 4))
        engines = data["engines"]
        brands = data["brands"]
        x = np.arange(len(engines))
        width = 0.22

        for i, brand in enumerate(brands):
            vals = [data["positions"].get(e, {}).get(brand) or 0 for e in engines]
            bars = ax.bar(x + i * width, vals, width, label=BRAND_DISPLAY[brand],
                         color=BRAND_COLORS[brand], edgecolor="white", linewidth=0.5)
            for bar, val in zip(bars, vals):
                if val > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                            f"#{val:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

        ax.set_ylabel("Avg Mention Position (lower = better)", fontsize=10)
        ax.set_title("Average Mention Position by LLM Engine", fontsize=13, fontweight="bold", pad=12)
        ax.set_xticks(x + width)
        ax.set_xticklabels([ENGINE_DISPLAY.get(e, e) for e in engines], fontsize=9)
        ax.invert_yaxis()
        ax.legend(fontsize=9, loc="lower right")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        return self._make_chart_image(fig, width=6.5, height=3.5)

    def _chart_citations(self, data):
        """Pie chart: Citation distribution."""
        fig, ax = plt.subplots(figsize=(5, 4))
        cs = data["citations"]
        labels = []
        sizes = []
        clrs = []
        if cs["on24_www"]:
            labels.append("ON24 (www)")
            sizes.append(cs["on24_www"])
            clrs.append("#0066CC")
        if cs["on24_event"]:
            labels.append("ON24 (event)")
            sizes.append(cs["on24_event"])
            clrs.append("#66AAEE")
        if cs["goldcast"]:
            labels.append("Goldcast")
            sizes.append(cs["goldcast"])
            clrs.append("#E8712B")
        if cs["zoom"]:
            labels.append("Zoom")
            sizes.append(cs["zoom"])
            clrs.append("#2D8CFF")
        if cs["other"]:
            labels.append("Other")
            sizes.append(cs["other"])
            clrs.append("#CCCCCC")

        if not sizes:
            ax.text(0.5, 0.5, "No citations found", ha="center", va="center", fontsize=12)
        else:
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=clrs, autopct="%1.0f%%",
                startangle=90, pctdistance=0.8, textprops={"fontsize": 9},
            )
            for txt in autotexts:
                txt.set_fontweight("bold")
                txt.set_fontsize(8)
        ax.set_title("Citation Distribution", fontsize=13, fontweight="bold", pad=12)
        fig.tight_layout()
        return self._make_chart_image(fig, width=4.5, height=3.5)

    def _chart_category_heatmap(self, data):
        """Heatmap: ON24 SOV by category and engine."""
        categories = sorted(data["cat_data"].keys())
        engines = data["engines"]

        fig, ax = plt.subplots(figsize=(8, max(3, len(categories) * 0.7 + 1)))
        matrix = []
        for cat in categories:
            row = []
            for eng in engines:
                sov = data["cat_data"].get(cat, {}).get(eng, {}).get("on24", {}).get("sov", 0)
                row.append(sov)
            matrix.append(row)

        matrix = np.array(matrix)
        im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0, vmax=100)

        ax.set_xticks(np.arange(len(engines)))
        ax.set_xticklabels([ENGINE_DISPLAY.get(e, e) for e in engines], fontsize=9)
        ax.set_yticks(np.arange(len(categories)))
        ax.set_yticklabels([CATEGORY_DISPLAY.get(c, c) for c in categories], fontsize=9)

        for i in range(len(categories)):
            for j in range(len(engines)):
                val = matrix[i, j]
                text_color = "white" if val > 60 else "black"
                ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                        fontsize=10, fontweight="bold", color=text_color)

        ax.set_title("ON24 Share of Voice by Category & Engine", fontsize=13, fontweight="bold", pad=12)
        fig.colorbar(im, ax=ax, label="SOV %", shrink=0.8)
        fig.tight_layout()
        return self._make_chart_image(fig, width=6.5, height=max(3, len(categories) * 0.6 + 1))

    # ── Table builders ────────────────────────────────────────
    def _kpi_cards(self, data, engine):
        """Build KPI card table for a specific engine."""
        brands = data["brands"]
        card_data = [
            [Paragraph(f"<b>{BRAND_DISPLAY[b]}</b>", self.styles["KPILabel"]) for b in brands],
        ]

        # SOV row
        sov_row = []
        for b in brands:
            val = data["sov"].get(engine, {}).get(b, 0)
            color = "#27AE60" if b == "on24" and val > 50 else "#333333"
            sov_row.append(Paragraph(f'<font color="{color}" size="18"><b>{val:.0f}%</b></font><br/>'
                                     f'<font size="8" color="#888">Share of Voice</font>',
                                     self.styles["KPILabel"]))
        card_data.append(sov_row)

        # Position row
        pos_row = []
        for b in brands:
            val = data["positions"].get(engine, {}).get(b)
            txt = f"#{val:.1f}" if val else "N/A"
            pos_row.append(Paragraph(f'<font size="18"><b>{txt}</b></font><br/>'
                                     f'<font size="8" color="#888">Avg Position</font>',
                                     self.styles["KPILabel"]))
        card_data.append(pos_row)

        # Win rate row
        wr_row = []
        for b in brands:
            val = data["win_rate"].get(engine, {}).get(b, 0)
            wr_row.append(Paragraph(f'<font size="18"><b>{val:.0f}%</b></font><br/>'
                                    f'<font size="8" color="#888">Win Rate</font>',
                                    self.styles["KPILabel"]))
        card_data.append(wr_row)

        # Sentiment row
        sent_row = []
        for b in brands:
            val = data["sentiment"].get(engine, {}).get(b, 0)
            color = "#27AE60" if val > 0.3 else "#E74C3C" if val < -0.1 else "#F39C12"
            sent_row.append(Paragraph(f'<font color="{color}" size="18"><b>{val:.2f}</b></font><br/>'
                                      f'<font size="8" color="#888">Sentiment</font>',
                                      self.styles["KPILabel"]))
        card_data.append(sent_row)

        col_width = 2.1 * inch
        tbl = Table(card_data, colWidths=[col_width] * len(brands))
        tbl.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return tbl

    def _search_term_table(self, data, engine):
        """Build per-query winner table for a specific engine."""
        queries = data["queries"]
        qw = data["query_winners"]

        header = [
            Paragraph("<b>Query</b>", self.styles["SmallText"]),
            Paragraph("<b>ON24</b>", self.styles["SmallText"]),
            Paragraph("<b>Goldcast</b>", self.styles["SmallText"]),
            Paragraph("<b>Zoom</b>", self.styles["SmallText"]),
            Paragraph("<b>Winner</b>", self.styles["SmallText"]),
        ]
        rows = [header]

        for qid in sorted(qw.keys()):
            if engine not in qw[qid]:
                continue
            q_data = qw[qid][engine]
            q_text = queries.get(qid, {}).get("query_text", f"Query {qid}")
            # Truncate
            if len(q_text) > 55:
                q_text = q_text[:52] + "..."

            brand_cells = []
            for brand in ["on24", "goldcast", "zoom"]:
                bd = q_data["brands"].get(brand, {})
                if bd.get("mentioned"):
                    pos = bd.get("position")
                    pos_txt = f"#{pos}" if pos else ""
                    sent = bd.get("sentiment")
                    sent_txt = f"{sent:.1f}" if sent is not None else ""
                    primary = " *" if bd.get("primary") else ""
                    cell_txt = f"{pos_txt} | {sent_txt}{primary}"
                    style = self.styles["SmallText"]
                else:
                    cell_txt = "-"
                    style = self.styles["SmallText"]
                brand_cells.append(Paragraph(cell_txt, style))

            winner = q_data.get("winner")
            winner_txt = BRAND_DISPLAY.get(winner, "-") if winner else "-"
            winner_color = BRAND_COLORS.get(winner, "#333333") if winner else "#333333"
            winner_cell = Paragraph(f'<font color="{winner_color}"><b>{winner_txt}</b></font>',
                                    self.styles["SmallText"])

            rows.append([
                Paragraph(q_text, self.styles["SmallText"]),
                *brand_cells,
                winner_cell,
            ])

        col_widths = [2.5 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch]
        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ON24_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    def _category_table(self, data, engine):
        """Category performance summary table."""
        header = [
            Paragraph("<b>Category</b>", self.styles["SmallText"]),
            Paragraph("<b>ON24 SOV</b>", self.styles["SmallText"]),
            Paragraph("<b>Goldcast SOV</b>", self.styles["SmallText"]),
            Paragraph("<b>Zoom SOV</b>", self.styles["SmallText"]),
            Paragraph("<b>ON24 Wins</b>", self.styles["SmallText"]),
        ]
        rows = [header]

        for cat in sorted(data["cat_data"].keys()):
            eng_data = data["cat_data"][cat].get(engine, {})
            on24 = eng_data.get("on24", {"sov": 0, "wins": 0, "total": 0})
            gc = eng_data.get("goldcast", {"sov": 0, "wins": 0, "total": 0})
            zm = eng_data.get("zoom", {"sov": 0, "wins": 0, "total": 0})

            rows.append([
                Paragraph(CATEGORY_DISPLAY.get(cat, cat), self.styles["SmallText"]),
                Paragraph(f'{on24["sov"]:.0f}%', self.styles["SmallText"]),
                Paragraph(f'{gc["sov"]:.0f}%', self.styles["SmallText"]),
                Paragraph(f'{zm["sov"]:.0f}%', self.styles["SmallText"]),
                Paragraph(f'{on24["wins"]}/{on24["total"]}', self.styles["SmallText"]),
            ])

        col_widths = [2.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 0.9 * inch]
        tbl = Table(rows, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ON24_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return tbl

    # ── Header / Footer ──────────────────────────────────────
    @staticmethod
    def _header_footer(canvas, doc):
        canvas.saveState()
        # Header line
        canvas.setStrokeColor(colors.HexColor("#0066CC"))
        canvas.setLineWidth(2)
        canvas.line(40, letter[1] - 35, letter[0] - 40, letter[1] - 35)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#AAAAAA"))
        canvas.drawString(40, letter[1] - 30, "ON24 GEO Benchmark Report")
        canvas.drawRightString(letter[0] - 40, letter[1] - 30, "CONFIDENTIAL")

        # Footer
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#AAAAAA"))
        canvas.drawString(40, 25, f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        canvas.drawRightString(letter[0] - 40, 25, f"Page {doc.page}")
        canvas.restoreState()

    # ── Main report builder ───────────────────────────────────
    def generate(self, run_id=None, output_path=None) -> str:
        """Generate the full PDF report. Returns the output file path."""
        data = self._load_data(run_id)

        if output_path is None:
            reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "output")
            os.makedirs(reports_dir, exist_ok=True)
            run_date = data["run"]["run_date"]
            output_path = os.path.join(reports_dir, f"ON24_GEO_Report_{run_date}.pdf")

        doc = SimpleDocTemplate(
            output_path, pagesize=letter,
            topMargin=0.6 * inch, bottomMargin=0.5 * inch,
            leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        )

        story = []

        # ─── COVER PAGE ──────────────────────────────────────
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("ON24 GEO Benchmark Report", self.styles["ReportTitle"]))
        story.append(Spacer(1, 0.2 * inch))
        story.append(HRFlowable(width="60%", thickness=2, color=ON24_BLUE,
                                spaceAfter=12, spaceBefore=6))
        story.append(Paragraph("Generative Engine Optimization Analysis", self.styles["ReportSubtitle"]))
        run_date = data["run"]["run_date"]
        story.append(Paragraph(f"Report Date: {run_date}", self.styles["ReportSubtitle"]))
        story.append(Spacer(1, 0.5 * inch))

        cover_info = [
            ["Benchmark Run", f"#{data['run_id']}"],
            ["Queries Analyzed", str(data["run"]["total_queries"])],
            ["LLM Engines", ", ".join(ENGINE_DISPLAY.get(e, e) for e in data["engines"])],
            ["Brands Tracked", "ON24, Goldcast, Zoom (Webinars/Events)"],
        ]
        cover_tbl = Table(cover_info, colWidths=[2 * inch, 4 * inch])
        cover_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), ON24_DARK),
            ("TEXTCOLOR", (1, 0), (1, -1), DARK_GRAY),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, MED_GRAY),
        ]))
        story.append(cover_tbl)
        story.append(Spacer(1, 1.0 * inch))
        story.append(Paragraph(
            '<font size="8" color="#AAAAAA">Prepared by ON24 GEO Benchmarking Tool | Confidential</font>',
            self.styles["ReportSubtitle"]
        ))
        story.append(PageBreak())

        # ─── TABLE OF CONTENTS ────────────────────────────────
        story.append(Paragraph("Table of Contents", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=12))
        toc_items = [
            "1. Executive Summary",
            "2. Methodology",
            "3. Results Overview",
            "4. Share of Voice Analysis",
            "5. Win Rate Analysis",
            "6. Mention Position Analysis",
            "7. Sentiment Analysis",
            "8. Citation Analysis",
            "9. Category Performance",
            "10. Search Term Breakdown",
            "11. Recommendations",
            "12. Glossary",
        ]
        for item in toc_items:
            story.append(Paragraph(item, ParagraphStyle(
                "TOC", parent=self.styles["BodyText"],
                fontSize=11, spaceBefore=4, spaceAfter=4, leftIndent=20,
            )))
        story.append(PageBreak())

        # ─── 1. EXECUTIVE SUMMARY ────────────────────────────
        story.append(Paragraph("1. Executive Summary", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))

        # Generate recommendations to get executive summary
        try:
            rec_engine = RecommendationEngine(self.db)
            recs = rec_engine.generate_recommendations(data["run_id"])
        except Exception:
            recs = {
                "executive_summary": "Recommendations could not be generated.",
                "wins": [], "losses": [], "recommendations": [],
                "competitor_insights": {
                    "goldcast": {"strengths": "N/A", "weaknesses": "N/A", "threat_level": "medium"},
                    "zoom": {"strengths": "N/A", "weaknesses": "N/A", "threat_level": "medium"},
                },
            }

        story.append(Paragraph(recs.get("executive_summary", ""), self.styles["BodyText"]))
        story.append(Spacer(1, 0.15 * inch))

        # KPI highlights for primary engine (grok preferred)
        primary_engine = "grok_web_search" if "grok_web_search" in data["engines"] else data["engines"][0]
        story.append(Paragraph(
            f"<b>Key Metrics — {ENGINE_DISPLAY.get(primary_engine, primary_engine)}</b>",
            self.styles["SubHeader"]
        ))
        story.append(self._kpi_cards(data, primary_engine))
        story.append(Spacer(1, 0.2 * inch))

        # Quick wins / losses bullets
        if recs.get("wins"):
            story.append(Paragraph("<b>Key Wins:</b>", self.styles["SubHeader"]))
            for w in recs["wins"][:5]:
                story.append(Paragraph(
                    f'<bullet>&bull;</bullet><b>{w.get("query", "")}</b> — {w.get("reason", "")}',
                    self.styles["BulletItem"]
                ))
            story.append(Spacer(1, 0.1 * inch))

        if recs.get("losses"):
            story.append(Paragraph("<b>Key Losses:</b>", self.styles["SubHeader"]))
            for l in recs["losses"][:5]:
                comp = l.get("winning_competitor", "competitor")
                story.append(Paragraph(
                    f'<bullet>&bull;</bullet><b>{l.get("query", "")}</b> — Lost to {comp}: {l.get("reason", "")}',
                    self.styles["BulletItem"]
                ))

        story.append(PageBreak())

        # ─── 2. METHODOLOGY ──────────────────────────────────
        story.append(Paragraph("2. Methodology", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))

        story.append(Paragraph(
            "This report analyzes ON24's visibility in AI-powered search results (Generative Engine "
            "Optimization, or GEO) compared to competitors <b>Goldcast</b> and <b>Zoom</b> "
            "(Webinars/Events only). The benchmark measures how each brand appears when users ask "
            "LLMs industry-relevant questions about webinar and virtual event platforms.",
            self.styles["BodyText"]
        ))

        story.append(Paragraph("<b>Query Library</b>", self.styles["SubHeader"]))
        story.append(Paragraph(
            f"<b>{data['run']['total_queries']}</b> search queries across 5 categories: "
            "Platform Comparison, Use Case, Feature, ROI/Strategy, and Technical. "
            "Each query represents a realistic B2B buyer search in an AI-powered engine.",
            self.styles["BodyText"]
        ))

        story.append(Paragraph("<b>LLM Engines Tested</b>", self.styles["SubHeader"]))
        engine_desc = {
            "grok_web_search": "Uses live web search via xAI Responses API. Returns real-time results with citations. Primary GEO benchmark.",
            "chatgpt_web_search": "Uses web search via OpenAI Responses API. The most widely used consumer AI search engine.",
            "claude_parametric": "Answers from training data only (no web search). Measures parametric knowledge — what the model inherently knows about ON24.",
        }
        for eng in data["engines"]:
            story.append(Paragraph(
                f'<bullet>&bull;</bullet><b>{ENGINE_DISPLAY.get(eng, eng)}</b> — {engine_desc.get(eng, "")}',
                self.styles["BulletItem"]
            ))

        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph("<b>Analysis Pipeline</b>", self.styles["SubHeader"]))
        pipeline_steps = [
            "Each query is sent to all LLM engines with a system prompt requesting detailed comparison.",
            "Responses are parsed by Claude to extract brand mentions, positions, sentiment, and citations.",
            "Metrics (SOV, position, sentiment, win rate) are computed per brand per query per engine.",
            "Winners are determined by: primary recommendation (+100), mention position (10/pos), sentiment (*5).",
            "Recommendations are generated by Claude analyzing the full dataset.",
        ]
        for i, step in enumerate(pipeline_steps, 1):
            story.append(Paragraph(
                f"<bullet>{i}.</bullet>{step}", self.styles["BulletItem"]
            ))

        story.append(PageBreak())

        # ─── 3. RESULTS OVERVIEW ─────────────────────────────
        story.append(Paragraph("3. Results Overview", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))

        for engine in data["engines"]:
            story.append(Paragraph(
                f"<b>{ENGINE_DISPLAY.get(engine, engine)}</b>", self.styles["SubHeader"]
            ))
            story.append(self._kpi_cards(data, engine))
            story.append(Spacer(1, 0.2 * inch))

        story.append(PageBreak())

        # ─── 4. SHARE OF VOICE ───────────────────────────────
        story.append(Paragraph("4. Share of Voice Analysis", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            "Share of Voice measures the percentage of queries where each brand is mentioned "
            "in the LLM response. Higher SOV indicates stronger brand presence in AI search results.",
            self.styles["BodyText"]
        ))
        story.append(self._chart_sov_comparison(data))
        story.append(PageBreak())

        # ─── 5. WIN RATE ─────────────────────────────────────
        story.append(Paragraph("5. Win Rate Analysis", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            "Win Rate measures the percentage of queries where each brand is determined to be the "
            "top recommendation. A 'win' is scored based on being the primary recommendation, "
            "being mentioned first, and having the highest sentiment score.",
            self.styles["BodyText"]
        ))
        story.append(self._chart_win_rate(data))
        story.append(PageBreak())

        # ─── 6. MENTION POSITION ─────────────────────────────
        story.append(Paragraph("6. Mention Position Analysis", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            "Mention Position tracks where each brand first appears in the LLM response. "
            "Position #1 means the brand is mentioned first — lower is better.",
            self.styles["BodyText"]
        ))
        story.append(self._chart_position(data))
        story.append(PageBreak())

        # ─── 7. SENTIMENT ────────────────────────────────────
        story.append(Paragraph("7. Sentiment Analysis", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            "Sentiment Score measures how positively or negatively each brand is described. "
            "Ranges from -1.0 (very negative) to +1.0 (very positive). "
            "Extracted by AI analyzing the context around each brand mention.",
            self.styles["BodyText"]
        ))
        story.append(self._chart_sentiment(data))
        story.append(PageBreak())

        # ─── 8. CITATION ANALYSIS ────────────────────────────
        story.append(Paragraph("8. Citation Analysis", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            f"<b>{data['total_citations']}</b> total citations extracted from LLM responses. "
            "Citations are URLs referenced by LLMs with web search enabled (Grok, ChatGPT). "
            "ON24 citations are split between <b>www.on24.com</b> (target — corporate site) and "
            "<b>event.on24.com</b> (webinar event pages).",
            self.styles["BodyText"]
        ))
        story.append(self._chart_citations(data))

        # Citation summary table
        cs = data["citations"]
        cite_rows = [
            [Paragraph("<b>Domain</b>", self.styles["SmallText"]),
             Paragraph("<b>Citations</b>", self.styles["SmallText"]),
             Paragraph("<b>%</b>", self.styles["SmallText"])],
        ]
        total = data["total_citations"] or 1
        for label, count in [("ON24 (www.on24.com)", cs["on24_www"]),
                             ("ON24 (event.on24.com)", cs["on24_event"]),
                             ("Goldcast", cs["goldcast"]),
                             ("Zoom", cs["zoom"]),
                             ("Other", cs["other"])]:
            cite_rows.append([
                Paragraph(label, self.styles["SmallText"]),
                Paragraph(str(count), self.styles["SmallText"]),
                Paragraph(f"{count/total*100:.1f}%", self.styles["SmallText"]),
            ])

        cite_tbl = Table(cite_rows, colWidths=[3 * inch, 1.2 * inch, 1.2 * inch])
        cite_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), ON24_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, MED_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(Spacer(1, 0.1 * inch))
        story.append(cite_tbl)
        story.append(PageBreak())

        # ─── 9. CATEGORY PERFORMANCE ─────────────────────────
        story.append(Paragraph("9. Category Performance", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            "Performance breakdown by query category, showing how ON24 performs across "
            "different topic areas.",
            self.styles["BodyText"]
        ))
        story.append(self._chart_category_heatmap(data))
        story.append(Spacer(1, 0.2 * inch))

        for engine in data["engines"]:
            story.append(Paragraph(
                f"<b>{ENGINE_DISPLAY.get(engine, engine)}</b>", self.styles["SubHeader"]
            ))
            story.append(self._category_table(data, engine))
            story.append(Spacer(1, 0.15 * inch))

        story.append(PageBreak())

        # ─── 10. SEARCH TERM BREAKDOWN ───────────────────────
        story.append(Paragraph("10. Search Term Breakdown", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))
        story.append(Paragraph(
            "Per-query analysis showing which brand wins each search term. "
            "Values show Position | Sentiment. <b>*</b> indicates primary recommendation.",
            self.styles["BodyText"]
        ))

        for engine in data["engines"]:
            story.append(Paragraph(
                f"<b>{ENGINE_DISPLAY.get(engine, engine)}</b>", self.styles["SubHeader"]
            ))
            story.append(self._search_term_table(data, engine))
            story.append(Spacer(1, 0.2 * inch))

        story.append(PageBreak())

        # ─── 11. RECOMMENDATIONS ─────────────────────────────
        story.append(Paragraph("11. Recommendations", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))

        if recs.get("on24_sov_assessment"):
            story.append(Paragraph(
                f"<b>SOV Assessment:</b> {recs['on24_sov_assessment']}", self.styles["BodyText"]
            ))
            story.append(Spacer(1, 0.1 * inch))

        if recs.get("recommendations"):
            for i, rec in enumerate(recs["recommendations"], 1):
                priority = rec.get("priority", i)
                impact = rec.get("expected_impact", "medium").upper()
                impact_color = {"HIGH": "#E74C3C", "MEDIUM": "#F39C12", "LOW": "#27AE60"}.get(impact, "#333")
                cat = rec.get("category", "")

                story.append(Paragraph(
                    f'<b>#{priority}. {rec.get("action", "")}</b> '
                    f'<font color="{impact_color}" size="8">[{impact} IMPACT]</font> '
                    f'<font color="#888" size="8">({cat})</font>',
                    self.styles["BodyText"]
                ))
                story.append(Paragraph(
                    f'<i>{rec.get("rationale", "")}</i>',
                    ParagraphStyle("RecRationale", parent=self.styles["BodyText"],
                                   leftIndent=20, textColor=colors.HexColor("#555555"))
                ))
                story.append(Spacer(1, 0.05 * inch))

        # Competitor insights
        if recs.get("competitor_insights"):
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph("<b>Competitor Insights</b>", self.styles["SubHeader"]))
            for comp in ["goldcast", "zoom"]:
                ci = recs["competitor_insights"].get(comp, {})
                if ci:
                    threat = ci.get("threat_level", "medium").upper()
                    threat_color = {"HIGH": "#E74C3C", "MEDIUM": "#F39C12", "LOW": "#27AE60"}.get(threat, "#333")
                    story.append(Paragraph(
                        f'<b>{BRAND_DISPLAY.get(comp, comp)}</b> '
                        f'<font color="{threat_color}" size="8">[{threat} THREAT]</font>',
                        self.styles["BodyText"]
                    ))
                    if ci.get("strengths"):
                        story.append(Paragraph(
                            f'<bullet>&bull;</bullet><b>Strengths:</b> {ci["strengths"]}',
                            self.styles["BulletItem"]
                        ))
                    if ci.get("weaknesses"):
                        story.append(Paragraph(
                            f'<bullet>&bull;</bullet><b>Weaknesses:</b> {ci["weaknesses"]}',
                            self.styles["BulletItem"]
                        ))
                    story.append(Spacer(1, 0.05 * inch))

        story.append(PageBreak())

        # ─── 12. GLOSSARY ────────────────────────────────────
        story.append(Paragraph("12. Glossary", self.styles["SectionHeader"]))
        story.append(HRFlowable(width="100%", thickness=1, color=ON24_BLUE, spaceAfter=10))

        glossary = {
            "GEO (Generative Engine Optimization)":
                "The practice of optimizing a brand's content and online presence to appear favorably in "
                "AI-generated search results. The AI equivalent of SEO.",
            "Share of Voice (SOV)":
                "The percentage of queries where a brand is mentioned at all in the LLM response. Higher is better.",
            "Mention Position":
                "The ordinal position where a brand first appears in an LLM response. Position #1 means "
                "the brand is mentioned first. Lower is better.",
            "Win Rate":
                "The percentage of queries where a brand is determined to be the top recommendation, "
                "based on primary recommendation status, mention position, and sentiment score.",
            "Sentiment Score":
                "A measure of how positively or negatively a brand is described. "
                "Ranges from -1.0 (very negative) to +1.0 (very positive).",
            "Primary Recommendation":
                "When an LLM explicitly recommends one brand as the top/best choice for the query.",
            "Citation":
                "A URL referenced by an LLM in its response. Grok and ChatGPT include citations with web search.",
            "Parametric Knowledge":
                "What an LLM knows from its training data, without accessing the web.",
            "Web Search (Live)":
                "When an LLM searches the internet in real-time to answer a query.",
        }

        for term, defn in glossary.items():
            story.append(Paragraph(f"<b>{term}</b>", self.styles["BodyText"]))
            story.append(Paragraph(
                defn, ParagraphStyle("GlossaryDef", parent=self.styles["BodyText"],
                                     leftIndent=20, spaceBefore=0, spaceAfter=8,
                                     textColor=colors.HexColor("#555555"))
            ))

        # ─── Build PDF ───────────────────────────────────────
        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        return output_path


def generate_report(run_id=None, output_path=None) -> str:
    """Convenience function to generate a PDF report."""
    gen = GEOReportGenerator()
    return gen.generate(run_id=run_id, output_path=output_path)


if __name__ == "__main__":
    path = generate_report()
    print(f"Report generated: {path}")
