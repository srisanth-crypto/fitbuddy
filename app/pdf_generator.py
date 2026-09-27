import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_plan_pdf(plan, user) -> io.BytesIO:
    """
    Generates a beautifully styled, production-grade PDF for a fitness plan
    using ReportLab. Returns an in-memory BytesIO stream.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom Palette
    primary_color = colors.HexColor("#4F46E5")   # Indigo
    secondary_color = colors.HexColor("#06B6D4") # Cyan
    dark_color = colors.HexColor("#0F172A")      # Slate 900
    light_bg = colors.HexColor("#F8FAFC")        # Slate 50
    accent_green = colors.HexColor("#059669")    # Emerald 600
    border_color = colors.HexColor("#E2E8F0")

    # Custom Paragraph Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=TA_LEFT
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_LEFT
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=dark_color,
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155")
    )

    day_heading_style = ParagraphStyle(
        'DayHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4
    )

    plan_line_style = ParagraphStyle(
        'PlanLine',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=2
    )

    # 1. Header Banner
    story.append(Paragraph("⚡ FITBUDDY – AI FITNESS PROGRAM", title_style))
    created_date = plan.created_at.strftime('%B %d, %Y') if getattr(plan, 'created_at', None) else datetime.now().strftime('%B %d, %Y')
    story.append(Paragraph(f"Personalized 7-Day Protocol • Generated on {created_date}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=4, spaceAfter=12))

    # 2. Athlete Metrics Profile Table
    athlete_data = [
        [
            Paragraph("<b>Athlete:</b>", body_style),
            Paragraph(str(user.username), body_style),
            Paragraph("<b>Target Goal:</b>", body_style),
            Paragraph(str(user.goal or "General Fitness"), body_style),
        ],
        [
            Paragraph("<b>User ID:</b>", body_style),
            Paragraph(str(user.user_id), body_style),
            Paragraph("<b>Workout Intensity:</b>", body_style),
            Paragraph(str(user.intensity or "Medium"), body_style),
        ],
        [
            Paragraph("<b>Age / Weight:</b>", body_style),
            Paragraph(f"{user.age or '--'} yrs / {user.weight or '--'} kg", body_style),
            Paragraph("<b>Plan Version:</b>", body_style),
            Paragraph("Revised with Feedback" if plan.updated_plan else "Original Program", body_style),
        ]
    ]

    metric_table = Table(athlete_data, colWidths=[85, 175, 105, 165])
    metric_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 12))

    # 3. Nutrition & Recovery Tip Box (if present)
    if plan.nutrition_tip:
        story.append(Paragraph("🥗 Nutrition & Recovery Blueprint", section_heading))
        cleaned_nutri = plan.nutrition_tip.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        for line in cleaned_nutri.split('\n'):
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith('###') or line_str.startswith('####'):
                header_title = line_str.lstrip('#').strip()
                story.append(Paragraph(f"<b>{header_title}</b>", day_heading_style))
            else:
                story.append(Paragraph(line_str, plan_line_style))
        story.append(Spacer(1, 10))

    # 4. 7-Day Workout Routine Output
    story.append(Paragraph("📅 7-Day Structured Workout Routine", section_heading))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceBefore=2, spaceAfter=8))
    
    workout_content = plan.updated_plan if plan.updated_plan else plan.original_plan
    cleaned_workout = workout_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    for line in cleaned_workout.split('\n'):
        line_str = line.strip()
        if not line_str or line_str == '---':
            continue
        if line_str.startswith('### DAY') or line_str.startswith('DAY '):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>{line_str.lstrip('#').strip()}</b>", day_heading_style))
        elif line_str.startswith('###'):
            story.append(Paragraph(f"<b>{line_str.lstrip('#').strip()}</b>", day_heading_style))
        elif line_str.startswith('>'):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<i>{line_str.lstrip('>').strip()}</i>", subtitle_style))
        else:
            story.append(Paragraph(line_str, plan_line_style))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=border_color, spaceBefore=4, spaceAfter=8))

    # 5. Footer Disclaimer
    footer_text = (
        "<i>FitBuddy AI Fitness Generator • Consult a healthcare or fitness professional before undertaking new physical training.</i>"
    )
    story.append(Paragraph(footer_text, subtitle_style))

    # Build Document
    doc.build(story)
    buffer.seek(0)
    return buffer
