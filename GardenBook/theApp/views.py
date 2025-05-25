from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.db.models import Count
import json
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from weasyprint import HTML
from .utils import generate_csv_books, generate_csv_guestsList, generate_csv_orders, generate_csv_payments, generate_csv_users, generate_event_pdf, generate_guest_list, generate_order_pdf, generate_order_report, generate_payment_report, generate_person_report, generate_stock_report, update_expired_reservations
from .models import Alert, Availability, Borrow, Genre, MembershipStatus, Order, Payment, Person, Book, ReadingHistory, Reservation, Review, RoleName, Wishlist, Event
from .forms import CustomBookEditingForm, CustomBookCreationForm, CustomPersonEditingForm, CustomOrderCreationForm, EventForm, ReaderCreationForm, ReviewForm, StaffCreationForm, SupplierForm
from django.db.models import Q,Sum,Min, Max,Avg
from django.core.paginator import Paginator
import uuid
from django.template.loader import render_to_string
from .decorators import role_required, owner_only, prevent_duplicate_borrow, prevent_duplicate_reservation
from dal import autocomplete


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
  # Update expired reservations
  update_expired_reservations()

  # Get new arrivals (e.g., last 3 books added)
  new_arrivals = Book.objects.order_by('-date_creation')[:3]

  # Get recommended books (e.g., most borrowed)
  recommended_books = Book.objects.order_by('-nb_borrows')[:3]

  # Book of the week (most liked or most reviewed this week)
  one_week_ago = timezone.now().date() - timedelta(days=7)
  book_of_week = (
    Book.objects
    .filter(reviews__created_at__gte=one_week_ago)
    .annotate(avg_rating=Avg('reviews__rating'))
    .order_by('-avg_rating')
    .first()
  )

  # Book of the month
  one_month_ago = timezone.now().date() - timedelta(days=30)
  book_of_month = (
    Book.objects
    .filter(reviews__created_at__gte=one_month_ago)
    .annotate(avg_rating=Avg('reviews__rating'))
    .order_by('-avg_rating')
    .first()
  )

  if book_of_month == None:
    book_of_month = Book.objects.first()
  if book_of_week is None:
    book_of_week = Book.objects.first()

  context = {
    'new_arrivals': new_arrivals,
    'recommended_books': recommended_books,
    'book_of_week': book_of_week,
    'book_of_month': book_of_month,
  }

  return render(request, 'home.html', context)

#_______________________________________________________________
def about(request):
  return render(request, 'about.html')

#_______________________________________________________________
# for the catalog page where all the books are displayed
# + a filter to see the wishlist(liked books)
def catalog(request):
  catalog = Book.objects.filter(~Q(availability=Availability.DELETED))

  wishlist_books = []
  if request.user.is_authenticated:
      wishlist_books = Wishlist.objects.filter(person=request.user).values_list('book_id', flat=True)


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
  book_count = Book.objects.filter(~Q(availability=Availability.DELETED)).count()

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
    'wishlist_books': list(wishlist_books),
  }

  return render(request, "catalog.html", context)

#_______________________________________________________________
# for displaying one book in detail
def book_detail(request, pk):
  book = Book.objects.get(id=pk)
  update_expired_reservations()

  wishlist = Wishlist.objects.filter(person=request.user, book=book).exists() if request.user.is_authenticated else False

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
      'form': form,
      'wishlist': wishlist,
  })

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
  orders = Order.objects.all().order_by('-order_date')
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
        return generate_order_pdf(request, order)  # Pass a list of orders, even if it's just one
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
@role_required(['Administrator', 'Librarian'])  # Optional, use only if role-based access is needed
def dashboard(request):
  now = timezone.now()
  start_of_month = now.replace(day=1)

  total_books = Book.objects.count()
  new_monthly_stock = Book.objects.filter(date_creation__gte=start_of_month).count()

  total_users = Person.objects.count()
  active_orders = Order.objects.filter(status='Pending').count()

  alerts = Alert.objects.select_related('user').order_by('-date_created')[:5]
  borrows = Borrow.objects.select_related('borrower', 'book').order_by('-borrow_date')[:5]
  total_borrows = Borrow.objects.count()

  # Borrowing trends data
  last_week = now - timedelta(days=6)
  weekly_borrows = (
      Borrow.objects
      .filter(borrow_date__gte=last_week)
      .annotate(day=TruncDay('borrow_date'))
      .values('day')
      .annotate(count=Count('id'))
      .order_by('day')
  )

  # Transform to dict
  weekly_labels = [entry['day'].strftime('%a') for entry in weekly_borrows]
  weekly_data = [entry['count'] for entry in weekly_borrows]

  # Monthly borrows
  monthly_borrows = (
      Borrow.objects
      .annotate(month=TruncMonth('borrow_date'))
      .values('month')
      .annotate(count=Count('id'))
      .order_by('month')
  )

  monthly_labels = [entry['month'].strftime('%b') for entry in monthly_borrows]
  monthly_data = [entry['count'] for entry in monthly_borrows]

  # Yearly borrows
  yearly_borrows = (
      Borrow.objects
      .annotate(year=TruncYear('borrow_date'))
      .values('year')
      .annotate(count=Count('id'))
      .order_by('year')
  )

  yearly_labels = [entry['year'].strftime('%Y') for entry in yearly_borrows]
  yearly_data = [entry['count'] for entry in yearly_borrows]

  genre_counts = Genre.objects.annotate(book_count=Count('book'))  # assuming related_name='book'
    
  categories_labels = [genre.name for genre in genre_counts]
  categories_data = [genre.book_count for genre in genre_counts]

  context = {
      'total_books': total_books,
      'new_monthly_stock': new_monthly_stock,
      'total_users': total_users,
      'active_orders': active_orders,
      'alerts': alerts,
      'borrows': borrows,
      'total_borrows': total_borrows,

      # Chart data as JSON
      'weekly_labels': json.dumps(weekly_labels),
      'weekly_data': json.dumps(weekly_data),
      'monthly_labels': json.dumps(monthly_labels),
      'monthly_data': json.dumps(monthly_data),
      'yearly_labels': json.dumps(yearly_labels),
      'yearly_data': json.dumps(yearly_data),

      'categories_labels': json.dumps(categories_labels),
      'categories_data': json.dumps(categories_data),


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
        print("Generating PDF")
        return generate_stock_report(request, filtered_books)
      elif format == 'csv':
        print("Generating CSV")
        return generate_csv_books(filtered_books)
      
      return redirect('stock')
    
  genres = Genre.objects.all()
  langs = Book.objects.values_list('lang', flat=True).distinct()
  auds = Book.objects.values_list('audience', flat=True).distinct()
  status = Availability.values

  # Get real min/max from DB for publication_year
  pub_year_stats = Book.objects.aggregate(pub_year_min=Min('publication_year'), pub_year_max=Max('publication_year'))
  pub_year_min = pub_year_stats['pub_year_min'] or 0
  pub_year_max = pub_year_stats['pub_year_max'] or 9999

  result_count = stock.count()
  book_count = Book.objects.filter(~Q(availability=Availability.DELETED)).count()

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
    'stock': stock,
    'status': status,
    }
  return render(request, 'stock.html', context)

#_______________________________________________________________
@login_required(login_url='login')
# for editing the information of a book 
def edit_book(request, pk):
  book = Book.objects.get(id = pk)

  form = CustomBookEditingForm(instance=book)
  if request.method == 'POST':
    form = CustomBookEditingForm(request.POST, instance=book, files=request.FILES)
    if form.is_valid():
      form.save()
      return redirect('stock')
  
  context = {'form' : form, 'book': book}
  return render(request, 'editBook.html', context)

#_______________________________________________________________
#for adding a new borrow made by user
@login_required(login_url='login')
@prevent_duplicate_borrow()
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
@prevent_duplicate_reservation()
def reserve(request, book_id):
  book = get_object_or_404(Book, id=book_id)
  print("Book found:", book)
  print("User trying to reserve:", request.user)
  
  Reservation.objects.create(
    person=request.user,
    book=book,
  )
  book.is_reserved = True
  book.save()
    
  return redirect('book-detail', pk=book.id)
#_______________________________________________________________
#for deleting a book (the book doesnt actually get deleted, 
# it is just not shown anymore in stock except for the admin)
@login_required(login_url='login')
def change_availability(request, pk, new_status):
  book = Book.objects.get(id=pk)
    # Check if new_status is a valid option in Availability
  if new_status in Availability.values:
    book.availability = new_status
    book.save()
    return redirect('stock')  # redirect back to the page you want
  

#_______________________________________________________________
# for the profile page. It will have this users info, borrowed books,
# the history of returned books, and reserved books
@login_required(login_url='login')
@owner_only(Person)
def profile(request, pk): 
  person = Person.objects.get(id = pk)

  borrowed_books = Borrow.objects.filter(borrower__id=pk)
  reserved_books = Reservation.objects.filter(person__id=pk)
  read_books =ReadingHistory.objects.filter(person__id=pk)
  wishlist = Wishlist.objects.filter(person=pk)
  alerts = Alert.objects.filter(user=person)
    

  context = {
    'person': person, 
    'borrowed_books': borrowed_books, 
    'reserved_books': reserved_books, 
    'read_books': read_books, 
    'wishlist': wishlist,
    'alerts': alerts,
    }
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

#_________________________________________________________
#for removing from wishlist
@login_required(login_url='login')
def remove_wishlist(request, book_id, user_id, current_page):
  user = Person.objects.get(id=user_id)
  book = Book.objects.get(id=book_id)

  # Check if the wishlist item exists
  wishlist_item = Wishlist.objects.filter(person=user, book=book).first()
  if wishlist_item:
    wishlist_item.delete()
    messages.success(request, "Book removed from your wishlist.")
  else:
    messages.info(request, "This book is not in your wishlist.")

  if current_page == 'profile':
    return redirect('profile', pk=user_id)
  else:
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
  available_books = Book.objects.filter(
    ~Q(availability=Availability.DELETED), 
    ~Q(availability=Availability.BORROWED)
    )
  if request.user.role == 'Librarian':
    users = users.filter(role=RoleName.READER)

  user_fines = {}

  # Single search input for ID, CIN, and Name
  q = request.GET.get('q')
  filters = Q()
  if q:
    filters &= (
      Q(id__icontains=q) |
      Q(cin__icontains=q) |
      Q(first_name__icontains=q) |
      Q(last_name__icontains=q)
    )

  # Other filters
  role = request.GET.get('role')
  dob = request.GET.get('dob')
  status = request.GET.get('membershipStatus')

  if role:
    filters &= Q(role__iexact=role)
  if dob:
    filters &= Q(dob=dob)
  if status:
    filters &= Q(status__iexact=status)

  users = users.filter(filters)

  # Calculate fines and update status
  for user in users:
    total_fine = Borrow.objects.filter(borrower=user, is_fine_paid=False).aggregate(total=Sum('fine'))['total'] or 0
    user_fines[user.id] = total_fine
    if total_fine > 0 and user.status != 'Suspended':
      user.status = 'Suspended'
      user.save(update_fields=['status'])

  if request.method == 'POST':
    action = request.POST.get('action')

    if action == 'print_users':
      format = request.POST.get('format')
      dob_from = request.POST.get('dob_from')
      dob_to = request.POST.get('dob_to')
      role = request.POST.get('role')
      status = request.POST.get('status')
      city = request.POST.get('city')
      country = request.POST.get('country')
      from_date_joined = request.POST.get('from_date_joined')
      to_date_joined = request.POST.get('to_date_joined')

      selected_users = users
      printing_filter = Q()

      if dob_from and dob_to:
        printing_filter &= Q(dob__range=[dob_from, dob_to])
      if role:
        printing_filter &= Q(role=role)
      if status:
        printing_filter &= Q(status=status)
      if city:
        printing_filter &= Q(city__icontains=city)
      if country:
        printing_filter &= Q(country__icontains=country)
      if from_date_joined and to_date_joined:
        printing_filter &= Q(date_joined__range=[from_date_joined, to_date_joined])
      
      if printing_filter:
        selected_users = selected_users.filter(printing_filter)

      if format == 'pdf':
        return generate_person_report(request, selected_users)
      elif format == 'csv':
        return generate_csv_users(selected_users)
      
    elif action == 'add_borrow':
      user_id = request.POST.get('user_id')
      raw_book = request.POST.get('book')
      print("Raw book:", raw_book)
      print("Raw borrower:", user_id)

      
      book_isbn = raw_book.split('-')[0].strip() if raw_book else None

      
      try:
        book = Book.objects.get(ISBN__icontains=book_isbn) if book_isbn else None
      except Book.DoesNotExist:
        book = None
      print("Book found:", book)
      # Look up borrower
      try:
        borrower = Person.objects.get(id=user_id) if user_id else None
      except Person.DoesNotExist:
        borrower = None
      print("Borrower found:", borrower)
      # Business logic
      if book and borrower:
        if book.availability == Availability.AVAILABLE:
          Borrow.objects.create(
            book=book,
            borrower=borrower,
            borrow_date=date.today(),
            due_date=date.today() + timedelta(days=14)
          )
          book.availability = Availability.BORROWED
          book.nb_borrows += 1
          book.save()
          messages.success(request, "Book borrowed successfully.")
        else:
          messages.error(request, "This book is not available for borrowing.")
      else:
        messages.error(request, "Invalid book or borrower selection.")

      return redirect('manage-users')
      
    
    return redirect('manage-users')
  print(available_books)
  context = {
    'users': users,
    'user_fines': user_fines,
    'available_books': available_books,
    }
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
  events = Event.objects.filter(is_cancelled=False)
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

  if request.method == 'POST':
    username = request.POST.get('username')
    email = request.POST.get('email')


    if username and email:
      #checks if the infos of the user are correct
      if request.user.username == username and request.user.email == email:
        #adds the user to the events guest list if he is not already in it
        if not Event.objects.filter(guests__username=username).exists():
          event = Event.objects.get(id=request.POST.get('event_id'))
          event.guests.add(request.user)
          messages.success(request, "You have been added to the guest list.")
        else:
          messages.info(request, "You are already on the guest list.")
      else:
        messages.error(request, "Username or email is incorrect.")
    else:
      messages.error(request, "Please fill in all fields.")



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
  users = Person.objects.all()
  available_books = Book.objects.filter(~Q(availability=Availability.DELETED), ~Q(availability=Availability.BORROWED))

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
        Reservation.objects.filter(book=borrow.book).update(status="Ready for pickup")
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


  borrows = borrows.order_by('-borrow_date')
  context = {
    'borrows': borrows,
    'users': users,
    'available_books': available_books,
    }
  return render(request, 'borrows_returns.html', context)

#________________________________________________________________
#for the payment page
@login_required(login_url='login')
def payment_page(request, pk, current_page):
  payer = Person.objects.get(id=pk)

  # Get all unpaid fines
  unpaid_fines = Borrow.objects.filter(borrower=payer, returned=True , fine__gt=0, is_fine_paid=False)
  
  total_fine = sum((fine.fine or Decimal("0.00")) for fine in unpaid_fines)

  if request.method == 'POST' and total_fine > 0:
    if current_page == 'profile':
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

      borrow.borrower.status = MembershipStatus.ACTIVE
      borrow.borrower.save()

      Payment.objects.create(
        transaction_Id=str(uuid.uuid4()),
        borrow=borrow,
        type_payment=type_payment,
        amount=borrow.fine,
        card_info=card_info
      )

    messages.success(request, "Payment successful.")
    if request.user.role == RoleName.READER:
      return redirect('profile', pk=payer.id)
    else:
      return redirect('borrows-returns')

  context = {
      'user': payer,
      'fines': unpaid_fines,
      'total_fine': total_fine,
  }
  if current_page == 'profile':
    return render(request, 'readerPay.html', context)
  else:
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
      user_id = request.POST.get('reader')
      book_id = request.POST.get('book')
      start_date = request.POST.get('start_date')
      end_date = request.POST.get('end_date')
      type_payment = request.POST.getlist('type_payment')

      # Start with all payments
      selected_payments = payments

      if user_id:
        selected_payments = selected_payments.filter(borrow__borrower__id=user_id)

      if book_id:
        selected_payments = selected_payments.filter(borrow__book__id=book_id)

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
def event_staff(request):
  events = Event.objects.all()
  query = request.GET.get("q", "")
  event_type = request.GET.get("event_type", "")
  date_filter = request.GET.get("date_filter", "")
  form = EventForm()
  

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

  # update the event status every time the page is loaded
  for event in events:
    if not event.is_cancelled:
      if event.end_datetime.date() < today:
          event.status = 'Completed'
      elif event.end_datetime.date() > today:
          event.status = 'Ongoing'
      else:
          event.status = 'Upcoming'
      event.save()


  context = {
      "events": events.order_by("-start_datetime"),
      "types": types,
      "form": form,
  }

  return render(request, "manage_event.html", context)

#________________________________________________________________
#for creating a new event
def create_event(request):
  if request.method == 'POST':
    form = EventForm(request.POST, request.FILES)
    if form.is_valid():
      event = form.save(commit=False)
      event.created_by = request.user
      event.save()
      return redirect('manage-event')


#_______________________________________________________________
#for canceling an event
def cancel_event(request, pk):
  event = Event.objects.get(id=pk)
  event.is_cancelled = True
  event.updated_by = request.user
  event.updated_at = date.today()
  event.save()
  return redirect('manage-event')

#_______________________________________________________________
#for generating a list of event guests
def generate_list(request, pk, format):
  event = Event.objects.get(id=pk)

  if format == 'pdf':
    return generate_guest_list(request, event)
  elif format == 'csv':
    return generate_csv_guestsList(event)
  
  return redirect('manage-event')

#_______________________________________________________________
#for printing an event
def print_event(request, pk):
  event = Event.objects.get(id=pk)
  return generate_event_pdf(request, event)

#_______________________________________________________________
#for sending a fine alert
def send_fine_alert(request, pk):
  user = Person.objects.get(id=pk)
  unreturned = Borrow.objects.filter(borrower=user, returned=False, is_fine_paid=False)


  alert_sent = False

  for borrow in unreturned:
    if borrow.fine and borrow.fine > 0:
      Alert.objects.create(
        user=user,
        title="Fine Alert",
        message=f"Your fine for the book '{borrow.book.title}' is {borrow.fine} MAD.",
      )
      user.unread_alerts += 1
      alert_sent = True

  if alert_sent:
    user.save()
    messages.success(request, f"Fine alert sent to {user.first_name} {user.last_name}.")
  else:
    messages.info(request, f"No unpaid fines for {user.first_name} {user.last_name}.")

  return redirect('manage-users')


#_______________________________________________________________
#for marking an alert as read
def mark_alert_read(request, pk):
  alert = Alert.objects.get(id=pk)
  user = Person.objects.get(id=alert.user.id)

  user.unread_alerts -= 1
  user.save()
  alert.is_read = True
  alert.save()
  return redirect('profile', pk=alert.user.id)

#_______________________________________________________________

