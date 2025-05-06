import csv
from django.http import HttpResponse,FileResponse
from io import BytesIO
# downloaded reportLab to generate a pdf "pip install reportlab"
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas



def generate_csv_orders(orders):
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


def generate_pdf_orders(orders):
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


#________________________________________________________________
def generate_csv_users(users):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_report.csv"'

    writer = csv.writer(response)

    writer.writerow(['ID', 'Full Name', 'Role', 'Status', 'City', 'Country', 'Date of Birth', 'Date Joined'])

    for user in users:
        writer.writerow([
            user.id,
            f"{user.first_name} {user.last_name}",
            user.role,
            user.status,
            user.city or '',
            user.country or '',
            user.dob or '',
            user.date_joined.date() if user.date_joined else ''
        ])

    return response

def generate_pdf_users(users):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    table_data = [
        ['ID', 'Full Name', 'Role', 'Status', 'City', 'Country', 'DOB', 'Date Joined']
    ]

    for user in users:
        table_data.append([
            user.id,
            f"{user.first_name} {user.last_name}",
            user.role,
            user.status,
            user.city or '',
            user.country or '',
            str(user.dob) if user.dob else '',
            user.date_joined.date() if user.date_joined else ''
        ])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#D3D3D3'),
        ('TEXTCOLOR', (0, 0), (-1, 0), '#000000'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, '#000000'),
    ]))

    doc.build([table])
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="users_report.pdf"'

    return response


#______________________________________________________________
def generate_pdf_books(books):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, y, "Book Stock Report")
    y -= 40

    p.setFont("Helvetica", 10)
    for book in books:
        if y < 100:
            p.showPage()
            y = height - 50

        line = f"{book.title} | {book.author} | {book.availability} | {book.lang} | Reserved: {book.is_reserved}"
        p.drawString(50, y, line)
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="books_report.pdf")

def generate_csv_books(books):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="books_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Title', 'Author', 'Availability', 'Language', 'Reserved'])

    for book in books:
        writer.writerow([book.title, book.author, book.availability, book.lang, 'Yes' if book.is_reserved else 'No'])

    return response

#_______________________________________________________________________________
def generate_pdf_user_detail(user):

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - inch
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "User Details Report")
    y -= 40

    p.setFont("Helvetica", 12)

    details = [
        ("CIN", user.cin),
        ("Full Name", f"{user.first_name} {user.last_name}"),
        ("Role", user.role),
        ("Date of Birth", user.dob.strftime("%Y-%m-%d") if user.dob else "N/A"),
        ("Phone", user.phone or "N/A"),
        ("Status", user.status),
        ("Address", user.address or "N/A"),
        ("City", user.city or "N/A"),
        ("Postal Code", user.postal_code or "N/A"),
        ("Country", user.country or "N/A"),
        ("Bio", user.bio or "N/A"),
    ]

    for label, value in details:
        p.drawString(80, y, f"{label}: {value}")
        y -= 20
        if y < 100:
            p.showPage()
            y = height - inch

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"user_{user.id}_details.pdf")

#_______________________________________________________________________
def generate_pdf_book_detail(book):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - inch
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, "Book Details Report")
    y -= 40

    p.setFont("Helvetica", 12)

    details = [
        ("ISBN", book.ISBN),
        ("Title", book.title),
        ("Author", book.author),
        ("Edition", book.edition),
        ("Availability", book.availability),
        ("Publication Year", book.publication_year.strftime("%Y-%m-%d") if book.publication_year else "N/A"),
        ("Pages", book.nbPage),
        ("Language", book.lang),
        ("Keywords", book.keywords),
        ("Description", book.description),
        ("Audience", book.audience),
        ("Review Score", book.review),
        ("Number of Borrows", book.nb_borrows),
        ("Creation Date", book.date_creation.strftime("%Y-%m-%d")),
        ("Reserved", "Yes" if book.is_reserved else "No")
    ]

    for label, value in details:
        p.drawString(80, y, f"{label}: {value}")
        y -= 20
        if y < 100:
            p.showPage()
            y = height - inch

    # Handle ManyToMany Field: Genres
    genre_list = ", ".join([genre.name for genre in book.genres.all()])
    p.drawString(80, y, f"Genres: {genre_list}")
    y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"book_{book.id}_details.pdf")



