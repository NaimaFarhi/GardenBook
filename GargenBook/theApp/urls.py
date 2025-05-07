from django.urls import path
from . import views

urlpatterns = [
  path('login', views.loginPage, name="login"),
  path('logout', views.logoutUser, name="logout"),
  path('register', views.registerReader, name="register"),


  path('', views.home, name="home"),

  path('manage-users', views.users, name="manage-users"),
  path('create-user', views.registerStaff, name="create-user"),
  path('profile/<str:pk>/', views.profile, name='profile'),
  path('edit-user/<str:pk>/', views.edit_user, name='edit-user'),
  path('change-account-status/<str:pk>/<str:new_status>', views.change_account_status, name='change-account-status'),
  path('print-user-details/<str:pk>', views.print_user_details, name='print-user-details'),
 
  path('catalog', views.catalog, name='catalog'),
  path('book-detail/<str:pk>/', views.book_detail, name='book-detail'),
  path('create-book', views.create_book, name='create-book'),
  path('stock', views.stock, name='stock'),
  path('edit-book/<str:pk>/', views.edit_book, name='edit-book'),
  path('change-availability/<str:pk>/<str:new_status>', views.change_availability, name='change-availability'),
  path('print-book-details/<str:pk>/', views.print_book_details, name='print-book-details'),
  
  path('orders', views.orders, name='orders'),
  path('dashboard', views.dashboard, name='dashboard'),
  path('events', views.events, name='events'),
  path('borrows-returns', views.borrowsReturns, name='borrows-returns'),
  path('add-wishlist/<str:book_id>/<str:user_id>/<str:current_page>', views.add_wishlist, name='add-wishlist'),
  path('reader_borrow/<str:book_id>', views.reader_borrow, name='reader-borrow'),
 
  path('payment/<int:pk>/', views.payment_page, name='payment-page'),


]