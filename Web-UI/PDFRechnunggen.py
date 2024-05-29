from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image
from io import BytesIO


def fmt_cents(cents):
    return "%.2f€" % (cents / 100)


def create_invoice(iban, rechnungsnr, date, total, total_discounted, name_vendor, invoice_notes, invoice_lines,
                   skonto_days, image_data=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, bottomMargin=50)
    styles = getSampleStyleSheet()

    title_style = styles['Title']
    title_style.fontSize = 18
    title_style.alignment = 1

    header_style = styles['Heading2']
    header_style.fontSize = 12
    header_style.textColor = colors.darkblue

    detail_style = ParagraphStyle('DetailStyle', parent=styles['Normal'], fontSize=10, spaceAfter=6)

    date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=8,
                                spaceAfter=6)
    invoice_num_style = ParagraphStyle('InvoiceNumStyle', parent=styles['Normal'], fontSize=20,
                                       spaceAfter=6)

    elements = []

    if image_data:
        img = Image(BytesIO(image_data))
        img.drawHeight = 1 * inch  # set height
        img.drawWidth = img.drawHeight * img.imageWidth / img.imageHeight  # calculate width based on original aspect ratio
        img.hAlign = 'RIGHT'  # Rechtsbündig ausrichten
        elements.append(img)
        elements.append(Spacer(1, 12))
    elements.append(Paragraph('Invoice', title_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"{date}", date_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"Invoice Number: {rechnungsnr}", invoice_num_style))
    elements.append(Spacer(1, 20))

    # Artikelübersicht
    elements.append(Paragraph("Following items have been purchased:", header_style))
    article_data = [['Item No.', 'Description', 'Quantity', 'Unit Price', 'Total']]
    article_data.extend(
        [[line['canon_id'], line['name'], line['quantity'], line['price_per_unit'], fmt_cents(line['total'])] for line
         in invoice_lines])

    total, total_discounted = fmt_cents(total), fmt_cents(total_discounted)
    article_data.append(["", "Total:", total, "Total after Skonto:", total_discounted])

    table = Table(article_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    # Skonto-Hinweis
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"We grant a Skonto discount on the invoice amount if payment is made within {skonto_days} days of the invoice date.",
        detail_style))

    # Zusätzliche Notizen
    if invoice_notes:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(invoice_notes, detail_style))

    # Footer mit Verkäufername
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        footer_text = f"{name_vendor}| {name_vendor}@gmail.com | IBAN: {iban} | CEO: Theus | Sitz der Gesellschaft: Berlin, Deutschland · Handelsregister: AG Berlin HRB 123456 · USt-IdNr. DE216398573"

        canvas.drawString(inch, 0.75 * inch, footer_text)
        canvas.restoreState()

    doc.build(elements, onFirstPage=footer, onLaterPages=footer)

    buffer.seek(0)
    return buffer.getvalue()
