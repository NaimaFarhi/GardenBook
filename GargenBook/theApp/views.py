from datetime import date, timedelta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .utils import generate_csv_books, generate_csv_orders, generate_csv_users, generate_pdf_book_detail, generate_pdf_books, generate_pdf_orders, generate_pdf_user_detail, generate_pdf_users
from .models import Availability, Borrow, Genre, Order, Person, Book, ReadingHistory, Reservation, Review, Wishlist, Event
from .forms import BorrowForm, CustomBookEditingForm, CustomBookCreationForm, CustomPersonEditingForm, CustomOrderCreationForm, ReaderCreationForm, ReviewForm, StaffCreationForm, SupplierForm
from django.db.models import Q,Sum,Min, Max
from django.core.paginator import Paginator

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
            status_filter = request.POST.getlist('status')  # Use getlist to handle multiple checkboxes
            
            # Filter orders based on date range and status
            selected_orders = Order.objects.filter(
                order_date__range=[start_date, end_date]
            )
            if status_filter:
                selected_orders = selected_orders.filter(status__in=status_filter)

            # Generate PDF or CSV for the filtered orders
            if request.POST.get('format') == 'pdf':
                return generate_pdf_orders(selected_orders)  # Generate PDF for multiple orders
            elif request.POST.get('format') == 'csv':
                return generate_csv_orders(selected_orders)  # Generate CSV for multiple orders
            
        elif action == 'add_supplier':
          formSupplier = SupplierForm(request.POST)
          if formSupplier.is_valid():
              formSupplier.save()
              return redirect('orders')
          
        elif action == 'add_order':
           formOrder = CustomOrderCreationForm(request.POST)
           if formOrder.is_valid():
              formOrder.save()
              return redirect('orders')
    
    formSupplier = SupplierForm()
    formOrder = CustomOrderCreationForm()
    context = {'orders': orders, 'formSupplier': formSupplier, 'formOrder': formOrder}
    return render(request, 'orders.html', context)

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

  if request.method == 'POST':
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

            # Handle export
            format = request.POST.get('format')
            if format == 'pdf':
                return generate_pdf_books(filtered_books)
            elif format == 'csv':
                return generate_csv_books(filtered_books)

  context = {'stock': stock}
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
          return generate_pdf_users(selected_users)
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

  # Filter by search keywords
  if query:
      events = events.filter(title__icontains=query) | events.filter(description__icontains=query)

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
      events = events.filter(start_datetime__date__range=[start_of_week, end_of_week])

  # Unique event types for the dropdown
  types = Event.objects.values_list("event_type", flat=True).distinct()

  context = {
      "events": events,
      "types": types,
  }

  return render(request, 'events.html', context)

#_______________________________________________________________
@login_required(login_url='login')
#for the borrows
def borrowsReturns(request):
  borrows = Borrow.objects.all()
  form = BorrowForm()

  if request.method == 'POST':
      action = request.POST.get('action')

      # Return a book
      if action == 'return_book':
        borrow_id = request.POST.get('borrow_id')
        borrow = Borrow.objects.get(id=borrow_id)

        # Mark book as returned
        borrow.return_date = date.today()
        if borrow.book.is_reserved:
          borrow.book.availability = 'Reserved'
        else:
          borrow.book.availability = 'Available'
        borrow.book.save()
        borrow.save()

        # Add to ReadingHistory
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
              if book.availability == 'Borrowed':
                  form.add_error('book', 'This book is currently borrowed.')
              else:
                  borrow = form.save(commit=False)
                  book.availability = 'Borrowed'
                  book.save()
                  borrow.save()
          return redirect('borrows-returns')

  context = {'borrows': borrows, 'form': form}
  return render(request, 'borrows_returns.html', context)

#________________________________________________________________
@login_required(login_url='login')
def payment_page(request, pk):
    user = Person.objects.get(id=pk)

    # Get all borrow entries with unpaid fines (e.g., returned = True, fine > 0, and not marked as paid)
    unpaid_fines = Borrow.objects.filter(borrower=user, returned=True, fine__gt=0, is_fine_paid=False)

    total_fine = sum(b.fine for b in unpaid_fines)

    if request.method == 'POST':
        # Dummy payment logic (add your gateway or Stripe integration here)
        for borrow in unpaid_fines:
            borrow.fine_paid = True
            borrow.save()

        messages.success(request, "Payment successful.")
        return redirect('Borrows-returns', user_id=user.id)  # or any success page

    context = {
        'user': user,
        'fines': unpaid_fines,
        'total_fine': total_fine,
    }
    return render(request, 'payment.html', context)




