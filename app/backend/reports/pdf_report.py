"""Compact PDF report for CSV Auto-Analyzer."""

from io import BytesIO
import re

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
)


def _safe_text(value, limit=180):
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _numeric_columns(df):
    cols = []
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            cols.append(col)
            continue
        converted = pd.to_numeric(
            s.astype(str).str.replace(",", "", regex=False)
            .str.replace("₹", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("%", "", regex=False),
            errors="coerce",
        )
        non_empty = s.notna().sum()
        if non_empty and converted.notna().sum() / non_empty >= 0.80:
            cols.append(col)
    return cols


def _chart_png(df, kind, x=None, y=None, title=""):
    """Create a compact matplotlib chart and return PNG bytes."""
    if df is None or df.empty:
        return None
    work = df.copy()

    if y and y in work.columns:
        work[y] = pd.to_numeric(work[y], errors="coerce")
        work = work.dropna(subset=[y])
    if work.empty:
        return None

    fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=150)

    try:
        if kind == "hist" and y:
            ax.hist(work[y], bins=18)
            ax.set_xlabel(y)
            ax.set_ylabel("Count")
        elif kind == "line" and x and y:
            temp = work[[x, y]].dropna().head(30)
            ax.plot(temp[x].astype(str), temp[y], marker="o", linewidth=1.8)
            ax.tick_params(axis="x", rotation=35, labelsize=7)
            ax.set_ylabel(y)
        elif kind == "bar" and x and y:
            temp = work[[x, y]].dropna().groupby(x, as_index=False)[y].sum()
            temp = temp.sort_values(y, ascending=False).head(10)
            ax.bar(temp[x].astype(str), temp[y])
            ax.tick_params(axis="x", rotation=35, labelsize=7)
            ax.set_ylabel(y)
        elif kind == "pie" and x:
            counts = work[x].astype(str).value_counts().head(8)
            if counts.empty:
                return None
            ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%", textprops={"fontsize": 7})
        else:
            return None

        ax.set_title(title, loc="left", fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.18)
        fig.tight_layout()

        out = BytesIO()
        fig.savefig(out, format="png", bbox_inches="tight", facecolor="white")
        out.seek(0)
        return out.getvalue()
    finally:
        plt.close(fig)


def _auto_chart_specs(df):
    nums = _numeric_columns(df)
    cats = [c for c in df.columns if c not in nums]
    specs = []

    if cats and nums:
        specs.append(("bar", cats[0], nums[0], f"{nums[0]} by {cats[0]}"))
    if len(nums) >= 2:
        specs.append(("bar", nums[0], nums[1], f"{nums[1]} by {nums[0]}"))
    if nums:
        specs.append(("hist", None, nums[0], f"Distribution of {nums[0]}"))
    if cats:
        specs.append(("pie", cats[0], None, f"{cats[0]} Distribution"))

    # Prefer a date trend when one is available.
    for col in df.columns:
        parsed = pd.to_datetime(df[col], errors="coerce")
        if parsed.notna().mean() >= 0.80 and nums:
            temp = df.copy()
            temp["__date__"] = parsed
            temp = temp.dropna(subset=["__date__", nums[0]])
            if not temp.empty:
                temp = temp.sort_values("__date__").head(60)
                specs.insert(0, ("line", "__date__", nums[0], f"{nums[0]} Trend"))
                return specs[:4], temp
    return specs[:4], df


def _table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def pdf_report(filename, df, kpis, insights, quality):
    """Return a compact, dashboard-style PDF as bytes."""
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=28,
        title=_safe_text(filename, 120),
        author="CSV Auto-Analyzer",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FileTitle", parent=styles["Title"], fontSize=20,
        leading=23, textColor=colors.HexColor("#172033"), alignment=TA_LEFT,
        spaceAfter=3,
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=8.5,
        textColor=colors.HexColor("#64748B"), spaceAfter=8,
    )
    h_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=12,
        leading=14, textColor=colors.HexColor("#172033"), spaceBefore=7, spaceAfter=5,
    )
    body = ParagraphStyle(
        "BodySmall", parent=styles["BodyText"], fontSize=8.5,
        leading=11, textColor=colors.HexColor("#334155"),
    )

    story = []

    # File name is the report identity; deliberately no generic report heading.
    story.append(Paragraph(_safe_text(filename, 100), title_style))
    story.append(Paragraph("CSV Auto-Analyzer • Executive dashboard", sub_style))

    # Dashboard box: dataset facts + KPIs.
    kpis = kpis or []
    cards = []
    for item in kpis[:4]:
        cards.append([
            Paragraph(f"<b>{_safe_text(item.get('name', 'KPI'), 35)}</b>", body),
            Paragraph(f"<b>{_safe_text(item.get('display_value', item.get('value', '—')), 28)}</b>", body),
        ])
    while len(cards) < 4:
        cards.append([Paragraph("<b>—</b>", body), Paragraph("<b>—</b>", body)])

    dashboard_data = [[
        Paragraph("<b>DASHBOARD</b>", body), Paragraph("<b>VALUE</b>", body),
        Paragraph("<b>DASHBOARD</b>", body), Paragraph("<b>VALUE</b>", body),
    ]]
    for a, b in zip(cards[::2], cards[1::2]):
        dashboard_data.append([a[0], a[1], b[0], b[1]])

    # Dataset facts are compact and replace the old wasteful data-summary section.
    dashboard_data.insert(1, [
        Paragraph(f"<b>Rows</b><br/>{len(df):,}", body),
        Paragraph(f"<b>Columns</b><br/>{len(df.columns):,}", body),
        Paragraph(f"<b>Numeric</b><br/>{len(_numeric_columns(df))}", body),
        Paragraph(f"<b>Health</b><br/>{quality.get('health_score', '—')}/100", body),
    ])

    dash = Table(dashboard_data, colWidths=[120, 70, 120, 70], hAlign="LEFT")
    dash.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#172033")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(dash)

    # Short insights only.
    story.append(Paragraph("Key Insights", h_style))
    if insights:
        for insight in insights[:6]:
            story.append(Paragraph(f"• {_safe_text(insight, 220)}", body))
    else:
        story.append(Paragraph("No major business insights were generated.", body))

    # Compact quality line.
    story.append(Paragraph("Data Quality", h_style))
    qdata = [["Health", "Missing", "Duplicates", "Outliers"], [
        f"{quality.get('health_score', '—')}/100",
        f"{quality.get('missing_cells', 0):,}",
        f"{quality.get('duplicate_rows', 0):,}",
        f"{quality.get('outlier_cells', 0):,}",
    ]]
    story.append(_table(qdata, [125, 125, 125, 125]))

    # Four compact charts, generated automatically from the same CSV.
    specs, chart_df = _auto_chart_specs(df)
    if specs:
        story.append(Paragraph("Dashboard Visuals", h_style))
        for kind, x, y, title in specs:
            if x == "__date__":
                # _chart_png accepts the temporary date column.
                pass
            png = _chart_png(chart_df, kind, x=x, y=y, title=title)
            if png:
                story.append(Image(BytesIO(png), width=245, height=105))
                story.append(Spacer(1, 4))

    # Missing details: only the top 5, so the report stays short.
    missing_table = quality.get("missing_table")
    if isinstance(missing_table, pd.DataFrame) and not missing_table.empty:
        story.append(Paragraph("Top Missing-Value Issues", h_style))
        rows = [["Column", "Missing", "%"]]
        for _, row in missing_table.head(5).iterrows():
            rows.append([
                Paragraph(_safe_text(row.get("Column", ""), 45), body),
                str(row.get("Missing Values", "")),
                f"{float(row.get('Missing %', 0)):.1f}%",
            ])
        story.append(_table(rows, [280, 110, 85]))

    document.build(story)
    output.seek(0)
    return output.getvalue()
