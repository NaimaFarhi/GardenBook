from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
import tempfile
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from weasyprint import HTML
from .utils import generate_csv_books, generate_csv_orders, generate_csv_payments, generate_csv_users, generate_pdf_book_detail, generate_pdf_books, generate_pdf_orders, generate_pdf_user_detail, generate_pdf_users
from .models import Availability, Borrow, EventType, Genre, Order, Payment, Person, Book, ReadingHistory, Reservation, Review, RoleName, Wishlist, Event
from .forms import BorrowForm, CustomBookEditingForm, CustomBookCreationForm, CustomPersonEditingForm, CustomOrderCreationForm, EventCreateForm, EventEditForm, ReaderCreationForm, ReviewForm, StaffCreationForm, SupplierForm
from django.db.models import Q,Sum,Min, Max
from django.core.paginator import Paginator
import uuid
from django.template.loader import render_to_string

#_____________________________________________________________


# for the login page
def loginPage(request):
  if request.method == 'POST':
    username = request.POST.get('username')
    password = request.POST.get('password')

    try:
      user = Person.objects.get(username=username)
    except:
      messages.error(request, "Username does not exist")

    user = authenticate(request, username=username, password=password)   

    if user is not None:
      login(request, user)

      if user.role == 'Reader':
        return redirect('home')
      else:
         return redirect('dashboard')
      
    else:
      messages.error(request, "Username or password is incorrect") 

  context = {}
  return render(request, "login.html", context)

#______________________________________________________________
# for the registration page for readers

def registerReader(request):
  form = ReaderCreationForm()
  if request.method == 'POST':
    form = ReaderCreationForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect('login')
  
  context = {'form' : form}
  return render(request, 'registrationForm.html', context)

#_______________________________________________________________

#for the logout
def logoutUser(request):
  logout(request)
  return redirect('home')

#_______________________________________________________________
#for the home page
def home(request):
  # Display new arrivals
  # Display recommendations
  # Display book of the week
  # Display book of the month
  return render(request, 'home.html')

#_______________________________________________________________
# for the catalog page where all the books are displayed
# + a filter to see the wishlist(liked books)
def catalog(request):
  catalog = Book.objects.filter(~Q(availability=Availability.REMOVED))

  # Search bar query
  q = request.GET.get('q')
  if q:
    catalog = catalog.filter(
        Q(ISBN__icontains=q) |
        Q(title__icontains=q) |
        Q(author__icontains=q) |
        Q(edition__icontains=q) |
        Q(keywords__icontains=q)
    )

  # Genre filter (multiple checkboxes)
  selected_genres = request.GET.getlist('genres')
  if selected_genres:
    catalog = catalog.filter(genre__name__in=selected_genres).distinct()

  # Publication year filter
  pub_year_from = request.GET.get('publicationYearFrom')
  pub_year_to = request.GET.get('publicationYearTo')
  if pub_year_from:
    catalog = catalog.filter(publication_year__gte=int(pub_year_from))
  if pub_year_to:
    catalog = catalog.filter(publication_year__lte=int(pub_year_to))

  # Language filter
  language = request.GET.get('language')
  if language:
    catalog = catalog.filter(lang__iexact=language)

  # Audience filter
  audience = request.GET.get('audience')
  if audience:
    catalog = catalog.filter(audience__iexact=audience)

  # Review filter
  review = request.GET.get('review')
  if review:
    catalog = catalog.filter(review__gte=int(review))

  # Dropdown/select data
  genres = Genre.objects.all()
  langs = Book.objects.values_list('lang', flat=True).distinct()
  auds = Book.objects.values_list('audience', flat=True).distinct()

  # Get real min/max from DB for publication_year
  pub_year_stats = Book.objects.aggregate(pub_year_min=Min('publication_year'), pub_year_max=Max('publication_year'))
  pub_year_min = pub_year_stats['pub_year_min'] or 0
  pub_year_max = pub_year_stats['pub_year_max'] or 9999

  result_count = catalog.count()
  book_count = Book.objects.filter(~Q(availability=Availability.REMOVED)).count()

  # Pagination
  paginator = Paginator(catalog, 12)  # 10 books per page
  page_number = request.GET.get('page')  # Get the current page number from URL
  page_obj = paginator.get_page(page_number)  # Get the page object
  
  context = {
    'page_obj': page_obj,
    'genres': genres,
    'langs': langs,
    'auds': auds,
    'pub_year_min': pub_year_min,
    'pub_year_max': pub_year_max,
    'result_count': result_count,
    'book_count': book_count,
  }

  return render(request, "catalog.html", context)

#_______________________________________________________________
# for displaying one book in detail
def book_detail(request, pk):
  book = Book.objects.get(id=pk)
  reviews = book.reviews.select_related('user')
  average = book.average_rating()
  form = ReviewForm()

  if request.method == 'POST':

    if request.user.is_authenticated:

      action = request.POST.get('action')
      
      # add a review 
      if action == 'add_review':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.update_or_create(
                user=request.user,
                book=book,
                defaults={'rating': form.cleaned_data['rating'], 'comment': form.cleaned_data['comment']}
            )
            return redirect('book-detail', pk=book.pk)
        
    else:
      return redirect('login')

  return render(request, 'book_detail.html', {
      'book': book,
      'reviews': reviews,
      'average_rating': average,
      'form': form
  })

#_____________________________________________________________
#for printing one books detrails
def print_book_details(request, pk):
  book = Book.objects.get(id=pk)
  return generate_pdf_book_detail(book)

#_______________________________________________________________

@login_required(login_url='login')
# for adding a new book to the stock
def create_book(request):
  form = CustomBookCreationForm()
  if request.method == 'POST':
    form = CustomBookCreationForm(request.POST, request.FILES)
    if form.is_valid():
      form.save()
      return redirect('stock')
  
  context = {'form' : form}
  return render(request, 'addBook.html', context)

#_______________________________________________________________
# for the orders page where the admin can see all the orders made by the users
@login_required(login_url='login')
#for orders page
def orders(request):
  orders = Order.objects.all()
  formSupplier = SupplierForm()
  formOrder = CustomOrderCreationForm()

  q = request.GET.get('q')
  status = request.GET.get('status')
  order_date = request.GET.get('order_date')

  if q:
    orders = orders.filter(
      Q(id__icontains=q) |
      Q(supplier__name__icontains=q) |
      Q(book__title__icontains=q)
    )

  if status:
      orders = orders.filter(status=status)

  if order_date:
      orders = orders.filter(order_date=order_date)

  # Get unique status values from existing orders
  status_choices = Order.objects.values_list('status', flat=True).distinct()
  
  if request.method == 'POST':
    print(request.POST)
    action = request.POST.get('action')

    # Update the status of an order
    if action == 'update_status':
      order_id = request.POST.get('order_id')
      order = Order.objects.get(id=order_id)
      status = request.POST.get('status')

      if order.status.lower() == "pending":  # the order can only be updated if it's pending
        order.status = status
        if status == "Delivered":
          order.delivery_date = date.today()
        order.updated_by = request.user
        order.updated_at = date.today()
        order.save()
        return redirect('orders')

    # Print one order (generate PDF/CSV for a single order)
    elif action == 'print_order':
      order_id = request.POST.get('order_id')
      order = Order.objects.get(id=order_id)
      
      if request.POST.get('format') == 'pdf':
        return generate_pdf_orders([order])  # Pass a list of orders, even if it's just one
      elif request.POST.get('format') == 'csv':
        return generate_csv_orders([order])  # samething here

    # Print a list of orders (generate PDF/CSV for multiple orders)
    elif action == 'print_multiple_orders':
      start_date = request.POST.get('from_date')
      end_date = request.POST.get('to_date')
      status_filter = request.POST.getlist('status')

      # Start with all orders
      selected_orders = orders

      # Filter by date range if valid
      if start_date and end_date:
        try:
          parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
          parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
          selected_orders = selected_orders.filter(order_date__range=[parsed_start, parsed_end])
        except ValueError:
          pass  # Skip filtering if dates are invalid

      # Filter by status if any
      if status_filter:
        selected_orders = selected_orders.filter(status__in=status_filter)

      # Generate report
      if request.POST.get('format') == 'pdf':
        return generate_order_report(request, selected_orders)
      elif request.POST.get('format') == 'csv':
        return generate_csv_orders(selected_orders)

            
    elif action == 'add_supplier':
      formSupplier = SupplierForm(request.POST)
      if formSupplier.is_valid():
        formSupplier.save()
        return redirect('orders')
      
    elif action == 'add_order':
      formOrder = CustomOrderCreationForm(request.POST)
      if formOrder.is_valid():
        order = formOrder.save(commit=False)
        order.created_by = request.user
        order.save()
        return redirect('orders')
  
  
  context = {
    'orders': orders,
    'formSupplier': formSupplier,
    'formOrder': formOrder,
    'status_choices': status_choices,
  }

  return render(request, 'orders.html', context)

#_______________________________________________________________
#for updating the status of an order
def update_order_status(request, pk, new_status):
  order = Order.objects.get(id=pk)
  if order.status.lower() == "pending":  # the order can only be updated if it's pending
    order.status = new_status
    if new_status == "Delivered":
      order.delivery_date = date.today()
    order.updated_by = request.user
    order.updated_at = date.today()
    order.save()
  return redirect('orders')

#_______________________________________________________________
# for the dashboard page where the admin can see the statistics of the library
@login_required(login_url='login')
#for the dashboard
def dashboard(request):
    total_books = Book.objects.count()
    total_users = Person.objects.count()
    active_orders = Order.objects.filter(status='Pending').count()
    context = {
        'total_books': total_books,
        'total_users': total_users,
        'active_orders': active_orders,
    }

    return render(request, 'dashboard.html', context)

#_______________________________________________________________
@login_required(login_url='login')
#shows all the books in stock
def stock(request):
  stock = Book.objects.all()

  if request.method == 'GET':
    q = request.GET.get('q')
    genres = request.GET.getlist('genre')
    publicationYearFrom = request.GET.get('publicationYearFrom')
    publicationYearTo = request.GET.get('publicationYearTo')
    language = request.GET.get('language')
    audience = request.GET.get('audience')
    review = request.GET.get('review')

    filters = Q()

    if q:
      filters &= (
        Q(title__icontains=q) |
        Q(ISBN__icontains=q) |
        Q(author__icontains=q) |
        Q(edition__icontains=q) |
        Q(keywords__icontains=q)
      )

    if genres:
      filters &= Q(genres__name__in=genres)

    if publicationYearFrom:
      try:
        filters &= Q(publication_year__gte=int(publicationYearFrom))
      except ValueError:
        pass

    if publicationYearTo:
      try:
        filters &= Q(publication_year__lte=int(publicationYearTo))
      except ValueError:
        pass

    if language:
      filters &= Q(lang__icontains=language)

    if audience:
      filters &= Q(audience=audience)

    if review:
      try:
        filters &= Q(review__gte=int(review))
      except ValueError:
        pass

    stock = stock.filter(filters).distinct()

  elif request.method == 'POST':
    action = request.POST.get('action')

    if action == 'print_stock':
      title = request.POST.get('title')
      author = request.POST.get('author')
      availability = request.POST.get('availability')
      lang = request.POST.get('lang')
      is_reserved = request.POST.get('is_reserved')

      filters = Q()

      if title:
        filters &= Q(title__icontains=title)
      if author:
        filters &= Q(author__icontains=author)
      if availability:
        filters &= Q(availability=availability)
      if lang:
        filters &= Q(lang__icontains=lang)
      if is_reserved == 'on':
        filters &= Q(is_reserved=True)

      filtered_books = Book.objects.filter(filters)

      format = request.POST.get('format')
      if format == 'pdf':
        return generate_stock_report(request, filtered_books)
      elif format == 'csv':
        return generate_csv_books( filtered_books)
      
  genres = Genre.objects.all()
  langs = Book.objects.values_list('lang', flat=True).distinct()
  auds = Book.objects.values_list('audience', flat=True).distinct()

  # Get real min/max from DB for publication_year
  pub_year_stats = Book.objects.aggregate(pub_year_min=Min('publication_year'), pub_year_max=Max('publication_year'))
  pub_year_min = pub_year_stats['pub_year_min'] or 0
  pub_year_max = pub_year_stats['pub_year_max'] or 9999

  result_count = stock.count()
  book_count = Book.objects.filter(~Q(availability=Availability.REMOVED)).count()

  # Pagination
  paginator = Paginator(stock, 15)  # 10 books per page
  page_number = request.GET.get('page')  # Get the current page number from URL
  page_obj = paginator.get_page(page_number)  # Get the page object
  
  context = {
    'page_obj': page_obj,
    'genres': genres,
    'langs': langs,
    'auds': auds,
    'pub_year_min': pub_year_min,
    'pub_year_max': pub_year_max,
    'result_count': result_count,
    'book_count': book_count,
    'stock': stock
    }
  return render(request, 'stock.html', context)



#_______________________________________________________________
@login_required(login_url='login')
# for editing the information of a book 
def edit_book(request, pk):
  book = Book.objects.get(id = pk)

  form = CustomBookEditingForm(instance=book)
  if request.method == 'POST':
    form = CustomBookEditingForm(request.POST, instance=book)
    if form.is_valid():
      form.save()
      return redirect('stock')
  
  context = {'form' : form, 'book': book}
  return render(request, 'editBook.html', context)

#_______________________________________________________________
#for adding a new borrow made by user
@login_required(login_url='login')
def reader_borrow(request, book_id):
  book = Book.objects.get(id=book_id)

  Borrow.objects.create(
    borrower=request.user,
    book=book,
    borrow_date=date.today()
  )
  book.availability = Availability.BORROWED
  book.nb_borrows += 1
  book.save()
  return redirect('book-detail', pk=book.pk)

#______________________________________________________________
@login_required(login_url='login')
def reserve(request, book_id):
  book = Book.objects.get(id=book_id)

  if not Borrow.objects.filter(person=request.user, book=book, returned=False, is_fine_paid=False).exists():
    Reservation.objects.create(
      person=request.user,
      book=book
    )

    book.is_reserved = True
    book.save()
    messages.success(request, "Book added to your Reservations.")
  else:
    messages.info(request, "You alrady borrowed this book.")
  return redirect('book-detail', pk=book.pk)

#_______________________________________________________________
@login_required(login_url='login')
#for deleting a book (the book doesnt actually get deleted, 
# it is just not shown anymore in stock except for the admin)
def change_availability(request, book_id, new_status):
  book = Book.objects.get(Book, id=book_id)
    # Check if new_status is a valid option in Availability
  if new_status in Book.Availability.values:
    book.availability = new_status
    book.save()
    return redirect('stock')  # redirect back to the page you want
  

#_______________________________________________________________
# for the profile page. It will have this users info, borrowed books,
# the history of returned books, and reserved books
@login_required(login_url='login')
def profile(request, pk): 
  person = Person.objects.get(id = pk)
  borrowed_books = Borrow.objects.filter(borrower__id=pk)
  reserved_books = Reservation.objects.filter(person__id=pk)
  read_books =ReadingHistory.objects.filter(person__id=pk)
  wishlist = Wishlist.objects.filter(person=pk)

  context = {'person': person, 'borrowed_books': borrowed_books, 'reserved_books': reserved_books, 'read_books': read_books, 'wishlist': wishlist}
  return render(request, 'profile.html', context)

#_________________________________________________________
#for adding to wishlist
@login_required(login_url='login')
def add_wishlist(request, book_id, user_id, current_page):
  user = Person.objects.get(id=user_id)
  book = Book.objects.get(id=book_id)

  # Check if the wishlist item already exists
  if not Wishlist.objects.filter(person=user, book=book).exists():
    Wishlist.objects.create(person=user, book=book)
    messages.success(request, "Book added to your wishlist.")
  else:
    messages.info(request, "This book is already in your wishlist.")

  return redirect(current_page)


#_______________________________________________________________
#for edit a users infos
@login_required(login_url='login')
def edit_user(request, pk): 
  person = Person.objects.get(id = pk)

  form = CustomPersonEditingForm(instance=person)
  if request.method == 'POST':
    form = CustomPersonEditingForm(request.POST, instance=person)
    if form.is_valid():
      form.save()
      return redirect('manage-users')
  
  context = {'form' : form, 'person': person}
  return render(request, 'editUser.html', context)

#_______________________________________________________________
# for the list of all type of users
@login_required(login_url='login')
def users(request):
  users = Person.objects.filter(is_superuser=False)
  user_fines = {}

  for user in users:
    total_fine = Borrow.objects.filter(borrower=user, is_fine_paid=False).aggregate(total=Sum('fine'))['total'] or 0
    user_fines[user.id] = total_fine

    #update the status to 'Suspended if the fines aren't paid
    if total_fine > 0 and user.status != 'Suspended':
      user.status = 'Suspended'
      user.save(update_fields=['status'])

  if request.method == 'POST':
    action = request.POST.get('action')

    if action == 'print_users':
      dob_from = request.POST.get('dob_from')
      dob_to = request.POST.get('dob_to')
      role = request.POST.get('role')
      status = request.POST.get('status')
      city = request.POST.get('city')
      country = request.POST.get('country')
      from_date_joined = request.POST.get('from_date_joined')
      to_date_joined = request.POST.get('to_date_joined')

      filters = Q()

      if dob_from and dob_to:
        filters &= Q(dob__range=[dob_from, dob_to])
      if role:
        filters &= Q(role=role)
      if status:
        filters &= Q(status=status)
      if city:
        filters &= Q(city__icontains=city)
      if country:
        filters &= Q(country__icontains=country)
      if from_date_joined and to_date_joined:
        filters &= Q(date_joined__date__range=[from_date_joined, to_date_joined])

      selected_users = Person.objects.filter(is_superuser=False).filter(filters)

      # Export
      if request.POST.get('format') == 'pdf':
          return generate_person_report(request, selected_users)
      elif request.POST.get('format') == 'csv':
          return generate_csv_users(selected_users)

  context = {'users': users, 'user_fines': user_fines}
  return render(request, 'manageUsers.html', context)

#________________________________________________________________
#for suspending/banning an account
def change_account_status(request, pk, new_status):
  user = Person.objects.get(id=pk)

  if new_status == 'Suspend':
    if user.status != 'Banned':
      user.status = 'Suspended'
      user.save()
      return redirect('manage-users')
    else:
      messages.warning(request, "This account is already banned. Go to Edit")
  else:
    user.status = 'Banned'
    user.save()
    return redirect('manage-users')

#______________________________________________________________
#for print a users informations
def print_user_details(request, pk):
  user = Person.objects.get(id=pk)
  return generate_pdf_user_detail(user)


#_______________________________________________________________
# for adding a new staff member
@login_required(login_url='login')
def registerStaff(request):
  form = StaffCreationForm()
  if request.method == 'POST':
    form = StaffCreationForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect('manage-users')
  
  context = {'form' : form}
  return render(request, 'addUser.html', context)

#_______________________________________________________________
@login_required(login_url='login')
#for events
def events(request):
  events = Event.objects.all()
  query = request.GET.get("q", "")
  event_type = request.GET.get("event_type", "")
  date_filter = request.GET.get("date_filter", "")
  page = request.GET.get("page", 1)

  # Filter by search keywords
  if query:
    events = events.filter(
      Q(title__icontains=query) | Q(description__icontains=query)
    )

  # Filter by event type
  if event_type:
    events = events.filter(event_type=event_type)

  # Filter by date
  today = timezone.now().date()
  if date_filter == "year":
    events = events.filter(start_datetime__year=today.year)
  elif date_filter == "month":
    events = events.filter(start_datetime__year=today.year, start_datetime__month=today.month)
  elif date_filter == "week":
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    events = events.filter(start_datetime__date__range=(start_of_week, end_of_week))

  # Pagination
  paginator = Paginator(events.order_by('start_datetime'), 5)  # 5 events per page
  page_obj = paginator.get_page(page)

  # Unique event types for filter dropdown
  types = Event.objects.values_list("event_type", flat=True).distinct()

  context = {
    "events": page_obj,
    "types": types,
    "query": query,
    "selected_type": event_type,
    "selected_date": date_filter,
  }

  return render(request, 'events.html', context)

#_______________________________________________________________
@login_required(login_url='login')
#for the borrows
def borrowsReturns(request):
  borrows = Borrow.objects.all()
  form = BorrowForm()

  # Filtering logic (GET request)
  if request.method == 'GET':
    q = request.GET.get('q')
    borrowed_on = request.GET.get('borrowed_on')
    due_date = request.GET.get('due_date')
    returned_on = request.GET.get('returned_on')

    if q:
      borrows = borrows.filter(
        Q(book__title__icontains=q) |
        Q(borrower__first_name__icontains=q) |
        Q(borrower__last_name__icontains=q)
      )

    if borrowed_on:
      borrows = borrows.filter(borrow_date=borrowed_on)

    if due_date:
      borrows = borrows.filter(due_date=due_date)

    if returned_on:
      borrows = borrows.filter(return_date=returned_on)

  # Action logic (POST request)
  elif request.method == 'POST':
    action = request.POST.get('action')

    if action == 'return_book':
      borrow_id = request.POST.get('borrow_id')
      borrow = Borrow.objects.get(id=borrow_id)

      # Update status and return date
      borrow.return_date = date.today()
      borrow.returned = True
      if borrow.book.is_reserved:
        borrow.book.availability = Availability.RESERVED
      else:
        borrow.book.availability = Availability.AVAILABLE

      borrow.book.save()
      borrow.save()

      # Log to reading history
      ReadingHistory.objects.create(
        person=borrow.borrower,
        book=borrow.book,
        date_borrowed=borrow.borrow_date,
        date_returned=borrow.return_date
      )

      return redirect('borrows-returns')

    elif action == 'add_borrow':
      form = BorrowForm(request.POST)
      if form.is_valid():
        book = form.cleaned_data['book']
        if book.availability == Availability.BORROWED:
          form.add_error('book', 'This book is currently borrowed.')
        else:
          borrow = form.save(commit=False)
          book.availability = Availability.BORROWED
          book.save()
          borrow.save()
      return redirect('borrows-returns')

  context = {'borrows': borrows, 'form': form}
  return render(request, 'borrows_returns.html', context)
  return render(request, 'borrows_returns.html', context)

#________________________________________________________________
#for the payment page
@login_required(login_url='login')
def payment_page(request, pk, current_page):
  payer = Person.objects.get(id=pk)

  # Get all unpaid fines
  unpaid_fines = Borrow.objects.filter(borrower=payer, returned=True , fine__gt=0, is_fine_paid=False)
  print(unpaid_fines)
  total_fine = sum((fine.fine or Decimal("0.00")) for fine in unpaid_fines)
  print(total_fine)

  if request.method == 'POST' and total_fine > 0:
    if current_page == 'pro':
      # Get card info from form
      card_name = request.POST.get('card_name')
      card_number = request.POST.get('card_number')
      expiry_date = request.POST.get('expiry_date')
      cvv = request.POST.get('cvv')
      type_payment = 'Card'
      card_info = f"{card_name}, {card_number}, {expiry_date}, {cvv}"
    else:
      # Librarian or admin paying in cash
      type_payment = 'Cash'
      card_info = '######PAID CASH######'

    # Save payment and mark each borrow as paid
    for borrow in unpaid_fines:
      borrow.is_fine_paid = True
      borrow.save()

      Payment.objects.create(
        transaction_Id=str(uuid.uuid4()),
        person=payer,
        borrow=borrow,
        type_payment=type_payment,
        amount=borrow.fine,
        card_info=card_info
      )

    messages.success(request, "Payment successful.")
    if request.user.role == RoleName.READER:
      return redirect('profile', user_id=payer.id)
    else:
      return redirect('borrows-returns')

  context = {
      'user': payer,
      'fines': unpaid_fines,
      'total_fine': total_fine,
  }
  return render(request, 'pay.html', context)

#________________________________________________________________
#for the staff payments page
def payment_staff(request):
  payments = Payment.objects.select_related('borrow__borrower', 'borrow', 'borrow__book')
  query = request.GET.get("q", "")
  type_payment = request.GET.get("type_payment", "")
  date_filter = request.GET.get("date", "")

  # Filter by search___________________
  # Search by person or transaction ID
  if query:
    payments = payments.filter(
      Q(borrow__borrower__first_name__icontains=query) |
      Q(borrow__borrower__last_name__icontains=query) |
      Q(borrow__borrower__email__icontains=query) |
      Q(borrow__borrower__cin__icontains=query) |
      Q(borrow__book__title__icontains=query) |
      Q(transaction_Id__icontains=query)
    )

  # Filter by payment type
  if type_payment:
    payments = payments.filter(type_payment__iexact=type_payment)

  # Filter by date
  if date_filter:
    try:
      selected_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
      payments = payments.filter(transaction_date__date=selected_date)
    except ValueError:
      pass  # Ignore invalid date

  #__Print a list of payments (generate PDF/CSV for multiple payments)
  if request.method == 'POST':
    action = request.POST.get('action')

    if action == 'print_payments':
      start_date = request.POST.get('start_date')
      end_date = request.POST.get('end_date')
      type_payment = request.POST.getlist('type_payment')

      # Start with all payments
      selected_payments = payments

      # Filter by date range if valid
      if start_date and end_date:
        try:
          parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
          parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
          selected_payments = selected_payments.filter(transaction_date__range=[parsed_start, parsed_end])
        except ValueError:
          pass  # Skip filtering if dates are invalid

      # Filter by payment type if any
      if any(type_payment):
        selected_payments = selected_payments.filter(type_payment__in=type_payment)

      # Generate report
      if request.POST.get('format') == 'pdf':
        return generate_payment_report(request, selected_payments)
      elif request.POST.get('format') == 'csv':
        return generate_csv_payments(selected_payments)

    return redirect('manage-payment')
      

  # Get unique payment types for filter dropdown
  transaction_users = Person.objects.filter(id__in=Payment.objects.values_list('borrow__borrower', flat=True).distinct())
  transaction_books = Book.objects.filter(id__in=Payment.objects.values_list('borrow__book', flat=True).distinct())


  context = {
    "payments": payments.order_by("-transaction_date"),
    "transaction_users": transaction_users,
    "transaction_books": transaction_books,
  }

  return render(request, "manage_payment.html", context)


#________________________________________________________________
def event_staff(request):
  events = Event.objects.all()
  query = request.GET.get("q", "")
  event_type = request.GET.get("event_type", "")
  date_filter = request.GET.get("date_filter", "")
  create_form = EventCreateForm()
  edit_forms = {event.id: EventEditForm(instance=event) for event in events}

  # Search
  if query:
    events = events.filter(
      Q(title__icontains=query) |
      Q(host__icontains=query) |
      Q(description__icontains=query)
    )

  # Filter by type
  if event_type:
    events = events.filter(event_type=event_type)

  # Filter by date
  today = timezone.now().date()
  if date_filter == "year":
    events = events.filter(start_datetime__year=today.year)
  elif date_filter == "month":
      events = events.filter(start_datetime__year=today.year, start_datetime__month=today.month)
  elif date_filter == "week":
      start_of_week = today - timedelta(days=today.weekday())
      end_of_week = start_of_week + timedelta(days=6)
      events = events.filter(start_datetime__date__range=(start_of_week, end_of_week))

  types = Event.objects.values_list("event_type", flat=True).distinct()

  context = {
      "events": events.order_by("-start_datetime"),
      "types": types,
      "create_form": create_form,
      "edit_forms": edit_forms,
  }

  return render(request, "manage_event.html", context)

#________________________________________________________________
#for creating a new event
def create_event(request):
  if request.method == 'POST':
    form = EventCreateForm(request.POST, request.FILES)
    if form.is_valid():
      event = form.save(commit=False)
      event.created_by = request.user
      event.save()
      return redirect('manage_events')

#_______________________________________________________________
#for canceling an event
def cancel_event(request, pk):
  event = Event.objects.get(id=pk)
  event.is_canceled = True
  event.updated_by = request.user
  event.updated_at = date.today()
  event.save()
  return redirect('manage_events')

#_______________________________________________________________
def generate_invoice(request, pk):
  payment = Payment.objects.get(id=pk)
  html_string = render_to_string('invoice.html', {'payment': payment})
  html = HTML(string=html_string, base_url=request.build_absolute_uri())

  pdf_file = html.write_pdf()

  response = HttpResponse(content_type='application/pdf')
  response['Content-Disposition'] = f'inline; filename="event_{payment.id}.pdf"'
  response.write(pdf_file)
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



