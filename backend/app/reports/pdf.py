import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_pdf(report, scan, top_findings, category_scores):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0F172A'),
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    heading1 = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=20,
        spaceAfter=15,
        borderWidth=1,
        borderColor=colors.HexColor('#CBD5E1'),
        borderPadding=5
    )
    
    normal = styles['Normal']
    
    story = []
    
    # TITLE PAGE
    story.append(Paragraph("CLOUDGUARD", title_style))
    story.append(Paragraph("AWS SECURITY ASSESSMENT", title_style))
    story.append(Spacer(1, 40))
    
    # Overview Table
    overview_data = [
        ["Report ID", report.id],
        ["Assessment Date", report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')],
        ["AWS Connection ID", scan.aws_connection_id if scan else 'N/A'],
        ["Scan ID", report.scan_id],
        ["Overall Security Score", f"{report.security_score} / 100" if report.security_score is not None else "Not Scored"],
        ["Security Rating", report.security_rating or "N/A"],
        ["Assessment Coverage", f"{report.coverage_percentage}%"],
        ["Total Resources Assessed", str(report.resource_count)],
        ["Total Findings", str(report.finding_count)],
    ]
    
    overview_table = Table(overview_data, colWidths=[200, 300])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8FAFC')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#334155')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
    ]))
    
    story.append(overview_table)
    story.append(PageBreak())
    
    # EXECUTIVE SUMMARY
    story.append(Paragraph("EXECUTIVE SUMMARY", heading1))
    exec_text = "No security findings were identified."
    if report.critical_count > 0:
        exec_text = "The assessment identified critical security issues requiring immediate attention."
    elif report.high_count > 0:
        exec_text = "The assessment found several high-priority security issues that should be addressed."
    elif report.finding_count > 0:
        exec_text = "The assessment identified security configuration issues that should be reviewed to improve security posture."
        
    story.append(Paragraph(exec_text, normal))
    story.append(Spacer(1, 15))
    
    # SECURITY POSTURE
    story.append(Paragraph("SECURITY POSTURE", heading1))
    
    finding_dist_data = [
        ["Severity", "Count"],
        ["CRITICAL", str(report.critical_count)],
        ["HIGH", str(report.high_count)],
        ["MEDIUM", str(report.medium_count)],
        ["LOW", str(report.low_count)],
        ["INFO", str(report.info_count)]
    ]
    
    dist_table = Table(finding_dist_data, colWidths=[100, 100])
    dist_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
    ]))
    story.append(dist_table)
    story.append(Spacer(1, 20))
    
    # CATEGORY SCORES
    if category_scores:
        story.append(Paragraph("CATEGORY SCORES", heading1))
        cat_data = [["Category", "Score"]]
        for cs in category_scores:
            cat_data.append([cs.category, str(cs.score)])
            
        cat_table = Table(cat_data, colWidths=[200, 100])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 8)
        ]))
        story.append(cat_table)
        story.append(PageBreak())
    
    # TOP FINDINGS
    story.append(Paragraph("TOP SECURITY FINDINGS", heading1))
    
    if not top_findings:
        story.append(Paragraph("No findings to report.", normal))
    else:
        for i, f in enumerate(top_findings):
            # Finding block
            f_title = ParagraphStyle('FTitle', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#0F172A'))
            story.append(Paragraph(f"{i+1}. {f.title}", f_title))
            
            sev_color = colors.grey
            if f.severity == "CRITICAL": sev_color = colors.HexColor('#DC2626')
            elif f.severity == "HIGH": sev_color = colors.HexColor('#EA580C')
            elif f.severity == "MEDIUM": sev_color = colors.HexColor('#CA8A04')
            elif f.severity == "LOW": sev_color = colors.HexColor('#2563EB')
            
            meta_data = [
                ["Severity:", f.severity],
                ["Service:", f.category],
                ["Resource:", f.resource_id]
            ]
            
            meta_table = Table(meta_data, colWidths=[80, 420])
            meta_table.setStyle(TableStyle([
                ('TEXTCOLOR', (1, 0), (1, 0), sev_color),
                ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 5))
            
            story.append(Paragraph("<b>Description:</b> " + (f.description or "N/A"), normal))
            story.append(Spacer(1, 3))
            story.append(Paragraph("<b>Recommendation:</b> " + (f.recommendation or "N/A"), normal))
            
            story.append(Spacer(1, 15))
            
    # END
    story.append(PageBreak())
    story.append(Paragraph("ASSESSMENT SCOPE", heading1))
    story.append(Paragraph("CloudGuard evaluates AWS configuration and security posture using the security rules enabled for this assessment. It does not inspect application file contents.", normal))
            
    doc.build(story)
    buffer.seek(0)
    return buffer
