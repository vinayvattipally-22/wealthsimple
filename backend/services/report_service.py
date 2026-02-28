"""PDF report generation using ReportLab."""
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_pdf_report(profile_data: dict, insights: list[dict], summary: dict) -> bytes:
    """Generate a branded PDF report of tax insights.

    Returns PDF content as bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=20, textColor=colors.HexColor("#0d3b66"))
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#0d3b66"), spaceAfter=8)
    body_style = styles["BodyText"]
    small_style = ParagraphStyle("Small", parent=body_style, fontSize=8, textColor=colors.grey)

    elements = []

    # Header
    elements.append(Paragraph("Wealthsimple AI Tax Analyzer", title_style))
    elements.append(Paragraph("Personalized Tax Insights Report", styles["Heading3"]))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0d3b66")))
    elements.append(Spacer(1, 12))

    # Profile summary
    employment = profile_data.get("employment", {})
    derived = profile_data.get("derived", {})
    income = employment.get("total_employment_income", 0)
    province = profile_data.get("province_code", "ON")
    tax_year = profile_data.get("tax_year", 2024)
    liability = derived.get("estimated_tax_liability", 0)
    marginal = derived.get("marginal_rate_combined", 0)

    elements.append(Paragraph("Personal Summary", heading_style))
    summary_data = [
        ["Tax Year", str(tax_year)],
        ["Province", province],
        ["Employment Income", f"${income:,.2f}"],
        ["Estimated Tax Liability", f"${liability:,.2f}"],
        ["Combined Marginal Rate", f"{marginal * 100:.1f}%"],
        ["Total Identified Savings", f"${summary.get('total_identified_savings', 0):,.2f}"],
    ]
    t = Table(summary_data, colWidths=[2.5 * inch, 3 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0d3b66")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Insights table
    if insights:
        elements.append(Paragraph("Tax Optimization Insights", heading_style))
        elements.append(Spacer(1, 4))

        table_data = [["Priority", "Category", "Insight", "Est. Value", "Action"]]
        for ins in insights:
            table_data.append([
                ins.get("priority", ""),
                ins.get("category", ""),
                ins.get("headline", "")[:60],
                f"${ins.get('estimated_value', 0):,.2f}" if ins.get("estimated_value") else "N/A",
                (ins.get("action_required", "") or "")[:50],
            ])

        col_widths = [0.7 * inch, 0.9 * inch, 2.5 * inch, 0.9 * inch, 2 * inch]
        t2 = Table(table_data, colWidths=col_widths, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(t2)
    else:
        elements.append(Paragraph("No insights available.", body_style))

    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 6))

    # Disclaimer
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y')} by Wealthsimple AI Tax Analyzer. "
        "This report is for informational purposes only and does not constitute tax advice. "
        "Please consult a qualified tax professional for personalized guidance.",
        small_style,
    ))

    doc.build(elements)
    return buf.getvalue()
