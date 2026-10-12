import io
import re
from datetime import datetime, timezone
from typing import List, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

# ==============================================================================
# 1. CREDENTIAL / SECRET SANITIZER
# ==============================================================================

SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(aws_secret_access_key|secret_key|secretkey|secret|password|passwd|pwd|token|jwt|session_token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'), r'\1=***REDACTED***'),
    (re.compile(r'eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]+'), r'***REDACTED_JWT***'),
    (re.compile(r'(?i)(aws_session_token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'), r'\1=***REDACTED***'),
    (re.compile(r'(?i)(access_key_id|accesskey|access_key)\s*[:=]\s*["\']?([A-Z0-9]{20})["\']?'), r'\1=***REDACTED***'),
]

def sanitize_text(text: Optional[str]) -> str:
    """Strip or redact any AWS secrets, tokens, passwords, or credentials."""
    if not text:
        return ""
    clean = str(text)
    for pattern, repl in SENSITIVE_PATTERNS:
        clean = pattern.sub(repl, clean)
    return clean


# ==============================================================================
# 2. NUMBERED CANVAS FOR DYNAMIC PAGE NUMBERS & HEADERS
# ==============================================================================

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to calculate total page count and render
    professional running headers and footers with page numbers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        
        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#0F172A"))
            self.drawString(40, 755, "CloudGuard")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(95, 755, "— AWS Security Assessment Report")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.75)
            self.line(40, 747, 572, 747)

        # Footer (All Pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(40, 42, 572, 42)
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(40, 30, "CloudGuard Assessment — Strictly Confidential")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(572, 30, page_str)
        self.restoreState()


# ==============================================================================
# 3. PDF GENERATION PIPELINE
# ==============================================================================

def generate_pdf(
    report: Any,
    scan: Any,
    findings: List[Any],
    category_scores: List[Any],
    account_id: Optional[str] = None,
) -> io.BytesIO:
    """
    Generate an executive-grade, deterministic AWS Security Assessment PDF.
    Guarantees strict score consistency and credential exclusion.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=45,
        bottomMargin=50,
    )

    base_styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    ACCENT = colors.HexColor("#0284C7")     # Sky 600
    MUTED = colors.HexColor("#64748B")      # Slate 500
    LIGHT_BG = colors.HexColor("#F8FAFC")   # Slate 50
    BORDER = colors.HexColor("#E2E8F0")     # Slate 200

    # Custom Typography Styles
    title_brand = ParagraphStyle(
        'DocBrand',
        parent=base_styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=ACCENT,
        spaceAfter=4,
    )

    title_main = ParagraphStyle(
        'DocTitle',
        parent=base_styles['Heading1'],
        fontSize=22,
        fontName='Helvetica-Bold',
        textColor=PRIMARY,
        spaceAfter=6,
    )

    subtitle = ParagraphStyle(
        'DocSub',
        parent=base_styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        textColor=MUTED,
        spaceAfter=15,
    )

    section_heading = ParagraphStyle(
        'SecHead',
        parent=base_styles['Heading2'],
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=8,
    )

    body_text = ParagraphStyle(
        'BodyTxt',
        parent=base_styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        textColor=colors.HexColor("#334155"),
        leading=13,
    )

    body_bold = ParagraphStyle(
        'BodyBld',
        parent=base_styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=PRIMARY,
    )

    score_num_style = ParagraphStyle(
        'ScoreNum',
        parent=base_styles['Normal'],
        fontSize=28,
        fontName='Helvetica-Bold',
        textColor=PRIMARY,
        alignment=TA_CENTER,
        leading=32,
    )

    score_label_style = ParagraphStyle(
        'ScoreLbl',
        parent=base_styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=MUTED,
        alignment=TA_CENTER,
    )

    story = []

    # --------------------------------------------------------------------------
    # HEADER / COVER SECTION
    # --------------------------------------------------------------------------
    story.append(Paragraph("CLOUDGUARD SECURITY", title_brand))
    story.append(Paragraph("AWS Security Assessment Report", title_main))
    
    gen_time_str = (
        report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        if hasattr(report, 'generated_at') and report.generated_at
        else datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    )
    story.append(Paragraph(f"Generated: {gen_time_str} &nbsp;|&nbsp; Report ID: {report.id}", subtitle))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=15))

    # --------------------------------------------------------------------------
    # EXECUTIVE POSTURE SUMMARY BOX (Score + Key Telemetry)
    # --------------------------------------------------------------------------
    score_display = f"{report.security_score}" if report.security_score is not None else "N/A"
    rating_display = sanitize_text(report.security_rating or "Not Scored")
    
    # Rating color
    if report.security_score is not None:
        if report.security_score >= 80:
            rating_color = colors.HexColor("#16A34A")  # Green
        elif report.security_score >= 60:
            rating_color = colors.HexColor("#D97706")  # Amber
        else:
            rating_color = colors.HexColor("#DC2626")  # Red
    else:
        rating_color = MUTED

    score_cell = [
        Paragraph("SECURITY SCORE", score_label_style),
        Spacer(1, 4),
        Paragraph(score_display, score_num_style),
        Spacer(1, 2),
        Paragraph(f'<font color="{rating_color.hexval()}"><b>{rating_display.upper()}</b></font>', score_label_style),
    ]

    resolved_account = account_id or (scan.account_id if hasattr(scan, "account_id") and scan.account_id else (scan.aws_connection_id if scan else "Primary"))

    meta_rows = [
        [Paragraph("Target AWS Account:", body_bold), Paragraph(sanitize_text(resolved_account), body_text)],
        [Paragraph("Scan Reference ID:", body_bold), Paragraph(sanitize_text(report.scan_id), body_text)],
        [Paragraph("Assessment Scope:", body_bold), Paragraph("IAM, S3, EC2, RDS, Network (SG), CloudTrail", body_text)],
        [Paragraph("Coverage / Scanned:", body_bold), Paragraph(f"{report.coverage_percentage}% &nbsp;|&nbsp; {report.resource_count} resources evaluated", body_text)],
        [Paragraph("Assessment Status:", body_bold), Paragraph(f"<b>{report.status}</b> ({getattr(scan, 'status', 'COMPLETED')})", body_text)],
    ]
    meta_table = Table(meta_rows, colWidths=[130, 240])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    summary_banner_table = Table(
        [[score_cell, meta_table]],
        colWidths=[150, 382],
    )
    summary_banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('LINEAFTER', (0, 0), (0, 0), 1, BORDER),
    ]))
    story.append(summary_banner_table)
    story.append(Spacer(1, 14))

    # --------------------------------------------------------------------------
    # EXECUTIVE NARRATIVE
    # --------------------------------------------------------------------------
    story.append(Paragraph("Executive Narrative", section_heading))
    if report.critical_count > 0:
        exec_narrative = (
            f"The deterministic security assessment of the target AWS infrastructure identified "
            f"<b>{report.critical_count} CRITICAL</b> vulnerabilities and <b>{report.high_count} HIGH</b> priority issues "
            f"requiring prompt remediation. Immediate focus is advised on public exposure and credential boundaries."
        )
    elif report.high_count > 0:
        exec_narrative = (
            f"The assessment identified <b>{report.high_count} HIGH</b> priority vulnerabilities across active AWS resources. "
            f"While no critical zero-day exposures were flagged, recommended configurations should be applied to prevent escalation."
        )
    elif report.finding_count == 0:
        exec_narrative = (
            "No security rule violations were identified across the discovered AWS resources. "
            "Configurations align with evaluated deterministic security baselines and encryption best practices."
        )
    else:
        exec_narrative = (
            f"The assessment identified <b>{report.finding_count}</b> non-critical configuration findings across the environment. "
            "Remediation guidelines are provided below to enhance security posture."
        )
    story.append(Paragraph(sanitize_text(exec_narrative), body_text))
    story.append(Spacer(1, 14))

    # --------------------------------------------------------------------------
    # SEVERITY BREAKDOWN & CATEGORY POSTURE
    # --------------------------------------------------------------------------
    story.append(Paragraph("Severity Summary & Category Breakdown", section_heading))

    # Severity Summary Table
    sev_header = [
        Paragraph("<b>CRITICAL</b>", ParagraphStyle('SevC', parent=base_styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor("#DC2626"), alignment=TA_CENTER)),
        Paragraph("<b>HIGH</b>", ParagraphStyle('SevH', parent=base_styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor("#EA580C"), alignment=TA_CENTER)),
        Paragraph("<b>MEDIUM</b>", ParagraphStyle('SevM', parent=base_styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor("#D97706"), alignment=TA_CENTER)),
        Paragraph("<b>LOW</b>", ParagraphStyle('SevL', parent=base_styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor("#2563EB"), alignment=TA_CENTER)),
        Paragraph("<b>INFO</b>", ParagraphStyle('SevI', parent=base_styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor("#059669"), alignment=TA_CENTER)),
        Paragraph("<b>TOTAL</b>", ParagraphStyle('SevT', parent=base_styles['Normal'], fontSize=8, fontName='Helvetica-Bold', textColor=PRIMARY, alignment=TA_CENTER)),
    ]
    sev_values = [
        Paragraph(str(report.critical_count), ParagraphStyle('SevValC', parent=base_styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#DC2626"), alignment=TA_CENTER)),
        Paragraph(str(report.high_count), ParagraphStyle('SevValH', parent=base_styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#EA580C"), alignment=TA_CENTER)),
        Paragraph(str(report.medium_count), ParagraphStyle('SevValM', parent=base_styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#D97706"), alignment=TA_CENTER)),
        Paragraph(str(report.low_count), ParagraphStyle('SevValL', parent=base_styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#2563EB"), alignment=TA_CENTER)),
        Paragraph(str(report.info_count), ParagraphStyle('SevValI', parent=base_styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#059669"), alignment=TA_CENTER)),
        Paragraph(str(report.finding_count), ParagraphStyle('SevValT', parent=base_styles['Normal'], fontSize=11, fontName='Helvetica-Bold', textColor=PRIMARY, alignment=TA_CENTER)),
    ]
    sev_table = Table([sev_header, sev_values], colWidths=[88, 88, 88, 88, 88, 92])
    sev_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(sev_table)
    story.append(Spacer(1, 10))

    # Category Scores Table (if available)
    if category_scores:
        cat_header = [
            Paragraph("Category", body_bold),
            Paragraph("Score", body_bold),
            Paragraph("Findings", body_bold),
            Paragraph("Crit / High", body_bold),
            Paragraph("Status", body_bold),
        ]
        cat_rows = [cat_header]
        for cs in category_scores:
            cat_name = getattr(cs, 'category', 'general').upper()
            cat_score = getattr(cs, 'score', 100)
            f_count = getattr(cs, 'finding_count', 0)
            ch_count = f"{getattr(cs, 'critical_count', 0)} / {getattr(cs, 'high_count', 0)}"
            st_badge = getattr(cs, 'status', 'SECURE')
            
            st_color = "#16A34A" if st_badge == "SECURE" else ("#DC2626" if st_badge == "DANGER" else "#D97706")
            
            cat_rows.append([
                Paragraph(cat_name, body_text),
                Paragraph(f"<b>{cat_score} / 100</b>", body_text),
                Paragraph(str(f_count), body_text),
                Paragraph(ch_count, body_text),
                Paragraph(f'<font color="{st_color}"><b>{st_badge}</b></font>', body_text),
            ])
            
        cat_table = Table(cat_rows, colWidths=[140, 95, 95, 95, 107])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ('BOX', (0, 0), (-1, -1), 1, BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(cat_table)

    story.append(Spacer(1, 14))

    # --------------------------------------------------------------------------
    # DETAILED FINDINGS & RECOMMENDATIONS SECTION
    # --------------------------------------------------------------------------
    story.append(Paragraph("Security Findings & Actionable Recommendations", section_heading))

    if not findings:
        story.append(Paragraph("No vulnerabilities were identified during this assessment. Good job maintaining security posture!", body_text))
    else:
        for idx, f in enumerate(findings):
            title = sanitize_text(getattr(f, 'title', 'Security Finding'))
            sev = (getattr(f, 'severity', 'INFO') or 'INFO').upper()
            res_id = sanitize_text(getattr(f, 'resource_id', 'N/A'))
            cat = sanitize_text(getattr(f, 'category', getattr(f, 'service', 'aws'))).upper()
            priority = sanitize_text(getattr(f, 'priority', 'P3'))
            risk = getattr(f, 'risk_score', 0)
            desc = sanitize_text(getattr(f, 'description', '') or 'No detailed description provided.')
            rec = sanitize_text(getattr(f, 'recommendation', '') or 'Inspect configuration and apply principle of least privilege.')

            # Severity badge styling
            if sev == "CRITICAL":
                badge_bg = "#FEE2E2"
                badge_fg = "#DC2626"
            elif sev == "HIGH":
                badge_bg = "#FFEDD5"
                badge_fg = "#EA580C"
            elif sev == "MEDIUM":
                badge_bg = "#FEF3C7"
                badge_fg = "#D97706"
            elif sev == "LOW":
                badge_bg = "#DBEAFE"
                badge_fg = "#2563EB"
            else:
                badge_bg = "#D1FAE5"
                badge_fg = "#059669"

            finding_header_html = (
                f'<b>{idx+1}. {title}</b> &nbsp;&nbsp;'
                f'<font color="{badge_fg}"><b>[{sev}]</b></font> &nbsp;'
                f'<font color="#64748B">({cat} &bull; {priority} &bull; Risk: {risk})</font>'
            )

            finding_content = [
                Paragraph(finding_header_html, body_bold),
                Spacer(1, 3),
                Paragraph(f"<b>Affected Resource:</b> <font face='Courier' size=8>{res_id}</font>", body_text),
                Spacer(1, 3),
                Paragraph(f"<b>Description:</b> {desc}", body_text),
                Spacer(1, 3),
                Paragraph(f"<b>Recommendation:</b> <font color='#0284C7'>{rec}</font>", body_text),
                Spacer(1, 8),
            ]

            story.append(KeepTogether(finding_content))

    story.append(Spacer(1, 10))

    # --------------------------------------------------------------------------
    # ASSESSMENT SCOPE & METHODOLOGY
    # --------------------------------------------------------------------------
    story.append(KeepTogether([
        Paragraph("Assessment Scope & Methodology", section_heading),
        Paragraph(
            "CloudGuard operates purely deterministically via AWS STS AssumeRole credentials. "
            "Evaluations analyze actual resource configuration attributes without reading application data, "
            "executing code, or modifying remote cloud resources. "
            "Assessments are zero-trust, automated, and strictly repeatable without reliance on non-deterministic AI models.",
            body_text,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>Audit Safety Guarantee:</b> No credentials, tokens, passwords, or persistent keys are stored or exposed in this report.",
            ParagraphStyle('SafeFoot', parent=body_text, fontName='Helvetica-Oblique', textColor=MUTED),
        ),
    ]))

    # Build PDF with dynamic page numbering
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
