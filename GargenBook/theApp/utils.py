import csv
from datetime import datetime
from django.http import HttpResponse
from io import BytesIO
from django.template.loader import render_to_string
from weasyprint import HTML

from .models import Order, Payment, Person, Book, Event



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

#________________________________________________________________
# For generating CVS for Payments
def generate_csv_payments(payments):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments_report.csv"'

    writer = csv.writer(response)

    # Write the header
    writer.writerow(['Payment Report'])

    writer.writerow(['Transaction ID', 'Reader', 'Book', 'Payment Type', 'Amount', 'Date'])

    for payment in payments:
        writer.writerow([
            payment.transaction_Id,
            f"{payment.person}",
            payment.borrow,
            payment.type_payment,
            payment.amount,
            payment.transaction_date.strftime("%Y-%m-%d") if payment.transaction_date else ''
        ])

    return response

#________________________________________________________________
def generate_csv_books(books):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="books_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ISBN', 'Title', 'Author', 'Availability', 'Language', 'Edition', 'Publication Year', 'Audience'])

    for book in books:
        writer.writerow([book.title, book.author, book.availability, book.lang, 'Yes' if book.is_reserved else 'No'])

    return response

#________________________________________________________________
def generate_csv_guestsList(event):
    guests = []

    if event.guests.exists():
        guests = event.guests.all()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reservations_report.csv"'

    writer = csv.writer(response)
    # Write the header  
    writer.writerow(['Guest List'])
    writer.writerow(['Event Title', event.title])
    writer.writerow(["Guest ID", "Username", "First Name", "Last Name", "email", "Phone"])

    for guest in guests:
        writer.writerow([guest.id,
            guest.username,
            guest.first_name,
            guest.last_name,
            guest.email,
            guest.phone,])

    return response

#________________________________________________________________






#___________________________PDF___________________________

# for generating the list of reservations
def generate_guest_list(request, event=None):
    if event is None:
        guests = []

    if event.guests.exists():
        guests = event.guests.all()
    
    # Define table columns
    columns = ["Guest ID", "Username", "First Name", "Last Name", "email", "Phone"]
    
    # Build rows
    rows = []
    for guest in guests:
        rows.append({
        "values": [
            guest.id,
            guest.username,
            guest.first_name,
            guest.last_name,
            guest.email,
            guest.phone,
        ]
        })
    
    total_guests = len(rows)
    cols = len(columns) - 1
    
    context = {
        "report": {
            "title": f"Guest List for {event.title}",
            "col": columns,
            "rows": rows,
            "total": f"{total_guests} Guests",
        },
        "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nbr_cols": cols,
        "request": request,
    }
    
    html_string = render_to_string("listTemplate.html", context)
    
    # Use in-memory buffer
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(target=pdf_file)
    
    # Build response
    pdf_file.seek(0)
    response = HttpResponse(pdf_file.read(), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="reservations_report.pdf"'
    
    return response


#________________________________________________________________
#for generating the stock report
def generate_stock_report(request, books=None):
  if books is None:
    books = Book.objects.all()

  # Define table columns
  columns = ["ISBN", "Title", "Author", "Edition", "Publication Year", "Audience", "Language"]

  # Build rows
  rows = []
  for book in books:
    rows.append({
      "values": [
        book.ISBN,
        book.title,
        book.author,
        book.edition,
        book.publication_year,
        book.audience,
        book.lang,
      ]
    })

  cols = len(columns) - 1
  total_books = len(rows)

  context = {
    "report": {
      "title": "Library Stock Report",
      "col": columns,
      "rows": rows,
      "total": f"{total_books} Books",
    },
    "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "nbr_cols": cols,
    "request": request,
  }

  html_string = render_to_string("listTemplate.html", context)

  # Use in-memory buffer
  pdf_file = BytesIO()
  HTML(string=html_string).write_pdf(target=pdf_file)

  # Build response
  pdf_file.seek(0)
  response = HttpResponse(pdf_file.read(), content_type="application/pdf")
  response["Content-Disposition"] = "inline; filename=stock_report.pdf"

  return response

#______________________________________________________________________
def generate_payment_report(request, payments=None):
  if payments is None:
    payments = Payment.objects.select_related("person", "borrow").all()

  # Define table columns
  columns = ["Transaction ID", "Reader", "Borrow", "Payment Type", "Card Info", "Transaction Date", "Amount"]

  # Build rows
  rows = []
  for payment in payments:
    rows.append({
      "values": [
        payment.transaction_Id,
        payment.borrow.borrower,
        payment.borrow.book,
        payment.type_payment,
        payment.card_info,
        payment.transaction_date.strftime("%Y-%m-%d %H:%M"),
        f"{payment.amount:.2f} MAD",
      ]
    })

  total_amount = sum(payment.amount for payment in payments)
  cols = len(columns) - 1

  context = {
    "report": {
      "title": "Payment Transactions Report",
      "col": columns,
      "rows": rows,
      "total": f"{total_amount:.2f} MAD",
    },
    "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "nbr_cols": cols,
    "request": request,
  }

  html_string = render_to_string("listTemplate.html", context)

  # Use in-memory buffer for PDF
  pdf_file = BytesIO()
  HTML(string=html_string).write_pdf(target=pdf_file)
  pdf_file.seek(0)

  # HTTP Response
  response = HttpResponse(pdf_file.read(), content_type="application/pdf")
  response["Content-Disposition"] = "inline; filename=payment_report.pdf"

  return response

#_______________________________________________________________________
def generate_person_report(request, people=None):
  if people is None:
    people = Person.objects.all()

  columns = ["Username", "CIN", "Full Name", "Role", "Date of Birth", "Phone", "Status", "City", "Country"]
  rows = []
  for person in people:
    rows.append({
      "values": [
        person.username,
        person.cin,
        f"{person.first_name} {person.last_name}",
        person.role,
        person.dob.strftime("%Y-%m-%d") if person.dob else "N/A",
        person.phone or "N/A",
        person.status,
        person.city or "N/A",
        person.country or "N/A",
      ]
    })

  context = {
    "report": {
      "title": "Library Members Report",
      "col": columns,
      "rows": rows,
      "total": f"{len(rows)} Members",
    },
    "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "nbr_cols": len(columns) - 1,
    "request": request,
  }

  html_string = render_to_string("listTemplate.html", context)
  pdf_file = BytesIO()
  HTML(string=html_string).write_pdf(target=pdf_file)
  pdf_file.seek(0)
  return HttpResponse(pdf_file.read(), content_type="application/pdf", headers={"Content-Disposition": "inline; filename=person_report.pdf"})

#_________________________________________________________________________________
def generate_order_report(request, orders=None):
  if orders is None:
    orders = Order.objects.select_related("book", "supplier", "created_by", "updated_by").all()

  columns = ["Order ID", "Book Title", "Supplier", "Status", "Order Date", "Expected Delivery", "Delivery Date", "Created By", "Updated By"]
  rows = []
  for order in orders:
    rows.append({
      "values": [
        order.id,
        order.book.title,
        order.supplier.name,
        order.status,
        order.order_date.strftime("%Y-%m-%d"),
        order.expected_delivery_date.strftime("%Y-%m-%d"),
        order.delivery_date.strftime("%Y-%m-%d") if order.delivery_date else "N/A",
        str(order.created_by) if order.created_by else "N/A",
        str(order.updated_by) if order.updated_by else "N/A",
      ]
    })

  context = {
    "report": {
      "title": "Order Report",
      "col": columns,
      "rows": rows,
      "total": f"{len(rows)} Orders",
    },
    "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "nbr_cols": len(columns) - 1,
    "request": request,
  }

  html_string = render_to_string("listTemplate.html", context)
  pdf_file = BytesIO()
  HTML(string=html_string).write_pdf(target=pdf_file)
  pdf_file.seek(0)
  return HttpResponse(pdf_file.read(), content_type="application/pdf", headers={"Content-Disposition": "inline; filename=order_report.pdf"})

#____________________________________________________________________________
def generate_event_report(request, events=None):
  if events is None:
    events = Event.objects.all()

  columns = ["Title", "Host", "Price", "Audience", "Type", "Location", "Start", "End", "Guests", "Status"]
  rows = []
  for event in events:
    status = "Canceled" if event.is_canceled else ("Public" if event.is_public else "Private")
    rows.append({
      "values": [
        event.title,
        event.host or "N/A",
        f"{event.event_price:.2f} MAD",
        event.audience,
        event.event_type,
        event.location,
        event.start_datetime.strftime("%Y-%m-%d %H:%M"),
        event.end_datetime.strftime("%Y-%m-%d %H:%M"),
        f"{event.current_reservations}/{event.nbr_reservations}",
        status,
      ]
    })

  context = {
    "report": {
      "title": "Event Report",
      "col": columns,
      "rows": rows,
      "total": f"{len(rows)} Events",
    },
    "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "nbr_cols": len(columns) - 1,
    "request": request,
  }

  html_string = render_to_string("listTemplate.html", context)
  pdf_file = BytesIO()
  HTML(string=html_string).write_pdf(target=pdf_file)
  pdf_file.seek(0)
  return HttpResponse(pdf_file.read(), content_type="application/pdf", headers={"Content-Disposition": "inline; filename=event_report.pdf"})

#____________________________________________________________________________
#for print the infos of one event
def generate_event_pdf(request, event=None):
    if event is None:
        event = Event.objects.first()  # or handle the case where no event is provided

        # key value pairs for the event
    event_details = {
        "Title": event.title,
        "Description": event.description,
        "Host": event.host,
        "Price": f"{event.event_price:.2f} MAD",
        "Audience": event.audience,
        "Type": event.event_type,
        "Location": event.location,
        "Start": event.start_datetime.strftime("%Y-%m-%d %H:%M"),
        "End": event.end_datetime.strftime("%Y-%m-%d %H:%M"),
        "Guests": f"{event.current_reservations}/{event.nbr_reservations}",
        "Status": "Canceled" if event.is_canceled else ("Public" if event.is_public else "Private"),
    }

    context = {
       "report": {
            "title": "Event Details",
            "details": event_details,
        },
        "current_date_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "request": request,
    }

    html_string = render_to_string("oneItemTemplate.html", context)

    # Use in-memory buffer
    pdf_file = BytesIO()
    HTML(string=html_string).write_pdf(target=pdf_file)

    # Build response
    pdf_file.seek(0)
    response = HttpResponse(pdf_file.read(), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="event_details.pdf"'

    return response
   
   

