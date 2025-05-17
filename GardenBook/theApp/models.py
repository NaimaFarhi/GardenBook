from datetime import date, timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
# Create your models here.

#_________________________________________________________________________
class PaymentType(models.TextChoices):
    CASH = 'Cash'
    CARD = 'Card'

#______________________________________________________________________________
class EventType(models.TextChoices):
    BOOK_READING = 'Book Reading'
    WORKSHOP = 'Workshop'
    AUTHOR_VISIT = 'Author Visit'
    EXHIBITION = 'Exhibition'
    OTHER = 'Other'

#______________________________________________________________________________
class RoleName(models.TextChoices):
    ADMIN = 'Administrator'
    LIBRARIAN = 'Librarian'
    READER = 'Reader'

#______________________________________________________________________________
class MembershipStatus(models.TextChoices):
    ACTIVE = 'Active'
    SUSPENDED = 'Suspended'
    BANNED = 'Banned'

#______________________________________________________________________________
class AudienceType(models.TextChoices):
   CHILDREN = "children"
   YA = "Young Adult"
   ADULT = "Adult"
   ALL = "All"

#______________________________________________________________________________
class Availability(models.TextChoices):
   AVAILABLE = "Available"
   RESERVED = "Reserved"
   BORROWED = "Borrowed"
   REMOVED = "Remove"

#______________________________________________________________________________
class Person(AbstractUser):
    cin = models.CharField(max_length=20, unique=True, default="")
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(max_length=20,choices=RoleName.choices, default=RoleName.READER)
    dob = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    bio = models.CharField(max_length=300, null=True, blank=True)
    unread_alerts = models.IntegerField(default=0)
    
    def __str__(self):
        return self.first_name + " " + self.last_name

    class Meta:
        ordering = ['-date_joined']


#______________________________________________________________________________
class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

#______________________________________________________________________________
class Book(models.Model):
    ISBN = models.CharField(max_length=13, unique=True)
    cover = models.ImageField(upload_to='book_covers/', null=True, blank=True, default="book_covers/default_cover.webp") # 'ImageField' handels image uploads
    # Installed "Pillow" using 'pip install Pillow'
    title = models.CharField(max_length=255,default="")
    author = models.CharField(max_length=255,default="")
    edition = models.CharField(max_length=255,default="")
    availability = models.CharField(max_length=30,choices=Availability.choices, default=Availability.AVAILABLE)
    publication_year = models.IntegerField(default=0)
    nbPage = models.IntegerField(default="")
    lang = models.CharField(max_length=244,default="")
    genres = models.ManyToManyField(Genre)
    keywords = models.CharField(max_length=244,default="")
    description = models.CharField(max_length=244,default="")
    audience = models.CharField(max_length=20, choices=AudienceType.choices, default="")
    review = models.IntegerField(default=0, validators=[
            MinValueValidator(0),  
            MaxValueValidator(10) 
        ])
    nb_borrows = models.IntegerField(default=0)
    date_creation = models.DateField(auto_now_add=True)
    date_modification = models.DateField(auto_now=True)
    is_reserved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.cover:
            # Set a default cover if none is provided
            self.cover = '/media/book_covers/default_cover.webp'
        super(Book, self).save(*args, **kwargs)

    def average_rating(self):
        reviews = self.reviews.all()
        return round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0

    def __str__(self):
        return self.title 

#______________________________________________________________________________
class Borrow(models.Model):
    borrower = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    borrow_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(default=date.today() + timedelta(days=15))
    return_date = models.DateField(null=True, blank=True)
    fine = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)# the fine should be updated every day
    is_fine_paid = models.BooleanField(default=False)
    returned = models.BooleanField(default=False)

    def __str__(self):
        return f"Borrow {self.id} - {self.book.title} by {self.borrower.username}"

    # Method that calculates the fine
    def calculate_fine(self):
        if self.return_date:
            late_days = (self.return_date - self.due_date).days
            self.returned = True
        else:
            late_days = (date.today() - self.due_date).days

        return 5 * max(late_days, 0)

    def save(self, *args, **kwargs):
        if self.return_date and not self.fine:
            self.fine = self.calculate_fine()
            if self.fine > 0:
                self.is_fine_paid = False

        super().save(*args, **kwargs)

#______________________________________________________________________________
class Reservation(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    reservation_date = models.DateField(auto_now_add=True, null=True, blank=True)
    expiration_date = models.DateField(default=date.today() + timedelta(days=2))
    status = models.CharField(max_length=20, choices=[('Waiting', 'Waiting'), ('Ready for pickup', 'Ready for pickup'), ('Expired', 'Expired')], default='Waiting')

    # Method to check if the reservation is expired
    def is_expired(self):
        return date.today() > self.expiration_date

    def __str__(self):
        return f"Reservation {self.id_reservation} - {self.book.title} by {self.person.username}"


#______________________________________________________________________________
class ReadingHistory(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    date_borrowed = models.DateField(auto_now_add=True)
    date_returned = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.person.username} - {self.book.title}"
    
#______________________________________________________________________________
class Supplier(models.Model):
    name = models.CharField(max_length=255, default="")
    email = models.EmailField(default="")
    phone = models.CharField(max_length=20, default="")
    address = models.TextField(default="")

    def __str__(self):
        return self.name
    
#______________________________________________________________________________
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Received', 'Received'),
        ('Cancelled', 'Cancelled'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="orders")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    order_date = models.DateField(auto_now_add=True)
    created_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders_created')
    expected_delivery_date = models.DateField()
    delivery_date = models.DateField(blank=True, null=True)
    updated_by = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders_updated')
    updated_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} - {self.book.title} ({self.status})"

#______________________________________________________________________________
class Wishlist(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.person.username} - {self.book.title}"    

#___________________________________________________________________________
class Review(models.Model):
    RATING_CHOICES = [(x / 2, str(x / 2)) for x in range(1, 11)]  # Allows 0.5 to 5 stars

    user = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.FloatField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')  # A user can only review a book once


#______________________________________________________________________________
class Event(models.Model):
    title = models.CharField(max_length=200)
    host = models.CharField(max_length=200, blank=True, null=True)
    poster = models.ImageField(upload_to='event_posters/', null=True, blank=True, default='event_posters/default_poster.jpg')
    description = models.TextField() 
    event_price = models.FloatField(default=0.0)
    audience = models.CharField(max_length=20, choices=AudienceType.choices, default="")
    location = models.CharField(max_length=255)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    nbr_reservations = models.IntegerField(default=0)
    current_reservations = models.IntegerField(default=0)
    guests = models.ManyToManyField(Person, blank=True, related_name='events')
    created_at = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default="")
    is_public = models.BooleanField(default=True)
    is_canceled = models.BooleanField(default=False)

    def __str__(self):
        return self.title


#______________________________________________________________________________
class Payment(models.Model):
    transaction_Id = models.CharField(max_length=70, unique=True)
    borrow = models.ForeignKey(Borrow, on_delete=models.CASCADE)
    type_payment = models.CharField(max_length=20, choices=PaymentType.choices, default="")
    amount = models.FloatField(default=0.0)
    #if its via card (cardholder name, card number, expiration date, cvv/cvc)
    # else will be filled with '######PAID CASH######'
    card_info = models.CharField(max_length=150, default="")
    transaction_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction_Id


class Alert(models.Model):
    user = models.ForeignKey(Person, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="")
    message = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    date_read = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Alert for {self.user.username} - {self.message[:20]}..."


