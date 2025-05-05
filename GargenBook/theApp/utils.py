import csv
from django.http import HttpResponse
from io import BytesIO
# downloaded reportLab to generate a pdf "pip install reportlab"
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle


def generate_csv(orders):
    # Create a response object and set content type for CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_report.csv"'

    # Create a CSV writer
    writer = csv.writer(response)

    # Write the header
    writer.writerow(['Order ID', 'Supplier', 'Book Title', 'Status', 'Order Date', 'Expected Delivery Date', 'Delivered On'])

    # Write the data for each order
    for order in orders:
        writer.writerow([order.id, order.supplier.name, order.book.title, order.status, order.order_date, order.expected_delivery_date, order.delivery_date])

    return response


def generate_pdf(orders):
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()

    # Create a PDF document object using the buffer
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Prepare the table data (header + order rows)
    table_data = [
        ['Order ID', 'Supplier', 'Book Title', 'Status', 'Order Date', 'Expected Delivery Date', 'Delivered On']
    ]

    # Add rows for each order
    for order in orders:
        table_data.append([
            order.id,
            order.supplier.name,
            order.book.title,
            order.status,
            order.order_date,
            order.expected_delivery_date,
            order.delivery_date or 'N/A',  # Handle missing delivery date
            order.updated_by or 'N/A',
            order.updated_at or 'N/A'
        ])

    # Create the table object
    table = Table(table_data)

    # Set table style (optional, to customize appearance)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#D3D3D3'),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), '#000000'),  # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center-align all cells
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font style
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),  # Regular font style for data rows
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Padding for header
        ('TOPPADDING', (0, 1), (-1, -1), 10),  # Padding for data rows
        ('GRID', (0, 0), (-1, -1), 1, '#000000'),  # Add gridlines
    ]))

    # Build the document with the table
    elements = [table]
    doc.build(elements)

    # Get PDF file data from the buffer
    pdf = buffer.getvalue()
    buffer.close()

    # Create a response to serve the PDF file
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="orders_report.pdf"'

    return response
