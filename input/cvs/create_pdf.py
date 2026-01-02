"""
Tạo file PDF trực tiếp từ JSON (không cần LaTeX)
Sử dụng ReportLab để tạo CV PDF chuyên nghiệp
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import KeepTogether
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


def create_cv_pdf(cv_data, output_path):
    """Tạo CV PDF từ dữ liệu JSON"""
    
    # Tạo document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.6*inch,
        bottomMargin=0.6*inch
    )
    
    # Container cho các elements
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2B4570'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2B4570'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        alignment=TA_JUSTIFY
    )
    
    contact_style = ParagraphStyle(
        'Contact',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=6
    )
    
    # Header - Tên
    name = cv_data['full_name']
    story.append(Paragraph(name, title_style))
    
    # Contact Info
    contact_info = f"{cv_data['email']} | {cv_data['phone']}"
    story.append(Paragraph(contact_info, contact_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Career Objective
    story.append(Paragraph("CAREER OBJECTIVE", section_style))
    years_exp = cv_data['work_experience']['total_years']
    role = cv_data['work_experience']['job_titles'][0]
    prog_langs = ', '.join(cv_data['hard_skills']['programming_languages'][:3])
    
    objective = f"Experienced {role} with {years_exp} years of expertise in software development and technology solutions. Seeking challenging opportunities to leverage technical skills and contribute to innovative projects. Strong background in {prog_langs} and modern development frameworks."
    story.append(Paragraph(objective, normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Education
    story.append(Paragraph("EDUCATION", section_style))
    university = cv_data['education_training']['universities'][0]
    degree = cv_data['education_training']['degrees'][0]
    major = cv_data['education_training']['majors'][0]
    
    edu_data = [
        [Paragraph(f"<b>{university}</b>", normal_style), "Sep 2017 - Jun 2021"],
        [Paragraph(f"{degree} in <b>{major}</b>", normal_style), ""]
    ]
    
    edu_table = Table(edu_data, colWidths=[5*inch, 1.5*inch])
    edu_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(edu_table)
    
    # Coursework
    story.append(Paragraph("• Relevant coursework: Data Structures, Algorithms, Software Engineering, Database Systems", normal_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Work Experience
    story.append(Paragraph("WORK EXPERIENCE", section_style))
    companies = cv_data['work_experience']['companies']
    job_titles = cv_data['work_experience']['job_titles']
    responsibilities = cv_data['responsibilities_achievements']['key_responsibilities']
    
    for i, company in enumerate(companies[:2]):
        title = job_titles[min(i, len(job_titles)-1)]
        years_ago = i + 1
        
        work_data = [
            [Paragraph(f"<b>{title}</b> at {company}", normal_style), f"Jan {2025-years_ago} - Present"]
        ]
        work_table = Table(work_data, colWidths=[5*inch, 1.5*inch])
        work_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        story.append(work_table)
        
        for resp in responsibilities[:3]:
            story.append(Paragraph(f"• {resp}", normal_style))
        
        story.append(Spacer(1, 0.15*inch))
    
    # Featured Projects
    story.append(Paragraph("FEATURED PROJECTS", section_style))
    projects = cv_data['responsibilities_achievements']['project_types']
    achievements = cv_data['responsibilities_achievements']['achievements']
    
    for project in projects[:2]:
        story.append(Paragraph(f"<b>{project}</b>", normal_style))
        for ach in achievements[:2]:
            story.append(Paragraph(f"• {ach}", normal_style))
        story.append(Spacer(1, 0.1*inch))
    
    # Skills
    story.append(Paragraph("SKILLS", section_style))
    
    # Technical Skills
    story.append(Paragraph("<b>Technical Skills</b>", normal_style))
    story.append(Paragraph(f"• <b>Languages:</b> {', '.join(cv_data['hard_skills']['programming_languages'])}", normal_style))
    story.append(Paragraph(f"• <b>Frameworks:</b> {', '.join(cv_data['hard_skills']['technologies_frameworks'][:5])}", normal_style))
    story.append(Paragraph(f"• <b>Tools:</b> {', '.join(cv_data['hard_skills']['tools_software'])}", normal_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Soft Skills
    story.append(Paragraph("<b>Soft Skills</b>", normal_style))
    comm_skills = cv_data['soft_skills']['communication_teamwork']
    leadership = cv_data['soft_skills']['leadership_management']
    
    for skill in comm_skills[:2]:
        story.append(Paragraph(f"• {skill}", normal_style))
    for skill in leadership[:2]:
        story.append(Paragraph(f"• {skill}", normal_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # Additional Information
    story.append(Paragraph("ADDITIONAL INFORMATION", section_style))
    story.append(Paragraph(f"• <b>Languages:</b> {', '.join(cv_data['additional_factors']['languages'])}", normal_style))
    story.append(Paragraph(f"• <b>Availability:</b> {cv_data['additional_factors']['availability']}", normal_style))
    story.append(Paragraph(f"• <b>Expected Salary:</b> {cv_data['additional_factors']['expected_salary']}", normal_style))
    
    if cv_data['hard_skills'].get('certifications'):
        certs = ', '.join(cv_data['hard_skills']['certifications'])
        story.append(Paragraph(f"• <b>Certifications:</b> {certs}", normal_style))
    
    # Build PDF
    doc.build(story)


def main():
    # Đường dẫn thư mục
    json_dir = Path(__file__).parent / "generated"
    
    if not json_dir.exists():
        print(f"Thư mục {json_dir} không tồn tại!")
        print("Vui lòng chạy create_cv.py trước để tạo file JSON.")
        return
    
    # Tìm tất cả file JSON
    json_files = sorted(json_dir.glob("cv_*.json"))
    
    if not json_files:
        print(f"Không tìm thấy file JSON nào trong {json_dir}")
        return
    
    print(f"\nBắt đầu tạo {len(json_files)} file PDF...")
    print("-" * 80)
    
    # Tạo PDF cho mỗi file JSON
    generated_pdfs = []
    
    for i, json_path in enumerate(json_files, 1):
        try:
            # Đọc dữ liệu JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                cv_data = json.load(f)
            
            # Tạo tên file PDF
            pdf_filename = json_path.stem + ".pdf"
            pdf_path = json_dir / pdf_filename
            
            # Tạo PDF
            create_cv_pdf(cv_data, pdf_path)
            
            generated_pdfs.append({
                'number': i,
                'name': cv_data['full_name'],
                'pdf_file': pdf_filename
            })
            
            # Progress indicator
            if i % 10 == 0:
                print(f"  Đã tạo {i}/{len(json_files)} PDFs...")
        
        except Exception as e:
            print(f"  ✗ Lỗi khi tạo PDF cho {json_path.name}: {str(e)}")
            continue
    
    # Báo cáo
    print("-" * 80)
    print(f"\n✓ Đã tạo {len(generated_pdfs)} file PDF tại: {json_dir}")
    
    print("\nDanh sách 10 file đầu tiên:")
    print("-" * 80)
    for item in generated_pdfs[:10]:
        print(f"{item['number']:3d}. {item['name']:30s}")
        print(f"     File: {item['pdf_file']}")
    print("-" * 80)
    
    if len(generated_pdfs) > 10:
        print(f"\n... và {len(generated_pdfs) - 10} file khác")
        print("-" * 80)


if __name__ == "__main__":
    main()
