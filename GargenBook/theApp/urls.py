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
  
  path('orders', views.orders, name='orders'),
  path('dashboard', views.dashboard, name='dashboard'),
  path('events', views.events, name='events'),
  path('borrows-returns', views.borrowsReturns, name='borrows-returns')

]