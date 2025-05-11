from django.contrib import admin
from .models import Alert, Payment, Person, Book, Genre, Borrow, ReadingHistory, Reservation, Order, Review, Supplier, Wishlist, RoleName, Event

# Unregister Borrow if already registered
try:
    admin.site.unregister(Borrow)
except admin.sites.NotRegistered:
    pass

# Custom BorrowAdmin to limit borrower to READER role
class BorrowAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "borrower":
            kwargs["queryset"] = Person.objects.filter(role=RoleName.READER)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# Register models with admin
admin.site.register(Person)
admin.site.register(Book)
admin.site.register(Genre)
admin.site.register(Borrow, BorrowAdmin)
admin.site.register(Reservation)
admin.site.register(Order)
admin.site.register(Supplier)
admin.site.register(ReadingHistory)
admin.site.register(Wishlist)
admin.site.register(Review)
admin.site.register(Event)
admin.site.register(Payment)
admin.site.register(Alert)