from django.contrib import admin
from .models import Person, Book, Genre, Borrow, ReadingHistory, Reservation, Order, Review, Supplier, Wishlist

# Register your models here.
admin.site.register(Person)
admin.site.register(Book)
admin.site.register(Genre)
admin.site.register(Borrow)
admin.site.register(Reservation)
admin.site.register(Order)
admin.site.register(Supplier)
admin.site.register(ReadingHistory)
admin.site.register(Wishlist)
admin.site.register(Review)

