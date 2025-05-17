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
 
  path('catalog', views.catalog, name='catalog'),
  path('book-detail/<str:pk>/', views.book_detail, name='book-detail'),
  path('create-book', views.create_book, name='create-book'),
  path('stock', views.stock, name='stock'),
  path('edit-book/<str:pk>/', views.edit_book, name='edit-book'),
  path('change-availability/<str:pk>/<str:new_status>', views.change_availability, name='change-availability'),
  
  path('orders', views.orders, name='orders'),
  path('update_order_status/<str:pk>/<str:new_status>', views.update_order_status, name='update_order_status'),
  path('dashboard', views.dashboard, name='dashboard'),
  path('events', views.events, name='events'),
  path('borrows-returns', views.borrowsReturns, name='borrows-returns'),
  path('add-wishlist/<str:book_id>/<str:user_id>/<str:current_page>', views.add_wishlist, name='add-wishlist'),
  path('reader_borrow/<str:book_id>', views.reader_borrow, name='reader-borrow'),
  path('reserve/<str:book_id>', views.reserve, name='reserve'),
 
  path('payment-page/<str:pk>/<str:current_page>', views.payment_page, name='payment-page'),
  path('generate_invoice/<int:pk>/', views.generate_invoice, name='generate_invoice'),
  path('manage-payment', views.payment_staff, name='manage-payment'),
  path('manage-event', views.event_staff, name='manage-event'),
  path('cancel-event/<str:pk>/', views.cancel_event, name='cancel-event'),
  path('create-event', views.create_event, name='create-event'),
  path('generate_list/<str:pk>/<str:format>', views.generate_list, name='generate_list'),
  path('print_event/<str:pk>/', views.print_event, name='print_event'),
  path('send_fine_alert/<str:pk>/', views.send_fine_alert, name='send_fine_alert'),
  path('mark-alert-read/<str:pk>/', views.mark_alert_read, name='mark-alert-read'),


]