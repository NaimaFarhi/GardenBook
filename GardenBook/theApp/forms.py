from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Borrow, Order, Person, Book, Review, RoleName, Supplier, Event
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Hidden

#_____________________________________________________
class CustomPersonCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Person
        fields = [
            'username', 'email', 'profile_pic', 'cin', 'first_name', 'last_name', 
            'password1', 'password2', 'role', 'dob', 'phone', 'status',
            'address','city', 'postal_code', 'country', 'bio'
        ]

        labels = {
            'username': 'Username',
            'email': 'Email',
            'profile_pic': 'Profile Picture',
            'cin': 'CIN',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'password1': 'Password',
            'password2': 'Confirm Password',
            'role': 'Role',
            'dob': 'Date of Birth',
            'phone': 'Phone Number',
            'status': 'Membership Status',
            'address': 'Address',
            'city': 'City',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'bio': 'Bio'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Create User', css_class="btn-green text-brown border-0 hover-shadow my-2"))

#____________________________________________________
class ReaderCreationForm(CustomPersonCreationForm):

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Person.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username
 
#__________________________________________________________
class StaffCreationForm(CustomPersonCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hide unnecessary fields
        self.fields['bio'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        full_name = cleaned_data.get('last_name') + cleaned_data.get('first_name')
        dob = cleaned_data.get('dob')

        if full_name and dob:
            username = f"{full_name.lower()}{dob.strftime('%Y%m%d')}"
           
            if Person.objects.filter(username=username).exists():
                raise forms.ValidationError("Generated username already exists. Please modify the first name")
            cleaned_data['username'] = username
            self.data = self.data.copy()
            self.data['username'] = username  # Update form input for re-rendering if needed

        return cleaned_data

#_______________________________________________________
class CustomPersonEditingForm(UserChangeForm):
    password = None  # hide the hashed password field

    class Meta:
        model = Person
        fields = [
            'username', 'email', 'profile_pic', 'cin', 'first_name', 'last_name',
            'dob', 'phone', 'address', 'status', 'role',
            'city', 'postal_code', 'country', 'bio'
        ]

        labels = {
            'username': 'Username',
            'email': 'Email',
            'profile_pic': 'Profile Picture',
            'cin': 'CIN',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'role': 'Role',
            'dob': 'Date of Birth',
            'phone': 'Phone',
            'status': 'Status',
            'address': 'Address',
            'city': 'City',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'bio': 'Bio'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Save', css_class="btn-green text-brown border-0 hover-shadow my-2"))

#________________________________________________________
class CustomBookCreationForm(forms.ModelForm):
    class Meta:
        model = Book
        exclude = ['likes', 'nb_borrows', 'availability', 'reserved']  # excluded from the form

        widgets = {
            'publication_year': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control my-3'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control my-3',
                'rows': 4,
                'placeholder': 'Enter a brief description of the book...'
            }),
            'keywords': forms.TextInput(attrs={
                'class': 'form-control my-3',
                'placeholder': 'e.g. science, magic, love'
            }),
            'lang': forms.TextInput(attrs={
                'class': 'form-control my-3',
                'placeholder': 'e.g. English'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control my-3'}),
            'author': forms.TextInput(attrs={'class': 'form-control my-3'}),
            'nbPage': forms.NumberInput(attrs={'class': 'form-control my-3'}),
            'ISBN': forms.TextInput(attrs={'class': 'form-control my-3'}),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-control my-3'}),
            'audience': forms.Select(attrs={'class': 'form-select my-3'}),
            'genres': forms.SelectMultiple(attrs={'class': 'form-select my-3'}),
        }

        labels = {
            'nbPage': 'Number of Pages',
            'lang': 'Language',
            'ISBN': 'ISBN Number',
            'cover': 'Cover Image',
            'title': 'Title',
            'author': 'Author',
            'publication_year': 'publication_year',
            'genres': 'Genres',
            'keywords': 'Keywords',
            'description': 'Description',
            'audience': 'Audience'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Create Book', css_class="btn-green text-brown border-0 hover-shadow my-2"))

#_________________________________________________________
class CustomBookEditingForm(forms.ModelForm):
    
    class Meta:
        model = Book
        exclude = ['likes', 'nb_borrows', 'reserved', 'review', 'date_creation']  # excluded from the form

        widgets = {
            'publication_year': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control my-3'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control my-3',
                'rows': 4,
                'placeholder': 'Enter a brief description of the book...'
            }),
            'keywords': forms.TextInput(attrs={
                'class': 'form-control my-3',
                'placeholder': 'e.g. science, magic, love'
            }),
            'lang': forms.TextInput(attrs={
                'class': 'form-control my-3',
                'placeholder': 'e.g. English'
            }),
            'title': forms.TextInput(attrs={'class': 'form-control my-3'}),
            'author': forms.TextInput(attrs={'class': 'form-control my-3'}),
            'nbPage': forms.NumberInput(attrs={'class': 'form-control my-3'}),
            'ISBN': forms.TextInput(attrs={'class': 'form-control my-3'}),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-control my-3'}),
            'audience': forms.Select(attrs={'class': 'form-select my-3'}),
            'availability': forms.Select(attrs={'class': 'form-select my-3'}),
            'genres': forms.SelectMultiple(attrs={'class': 'form-select my-3'}),
        }

        labels = {
            'nbPage': 'Number of Pages',
            'lang': 'Language',
            'ISBN': 'ISBN Number',
            'cover': 'Cover Image',
            'title': 'Title',
            'author': 'Author',
            'publication_year': 'publication_year',
            'genres': 'Genres',
            'keywords': 'Keywords',
            'description': 'Description',
            'audience': 'Audience'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Save Changes', css_class="btn-green text-brown border-0 hover-shadow my-2"))

#______________________________________________________________
class CustomOrderCreationForm(forms.ModelForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='add_order')  

    class Meta:
        model = Order
        fields = ['supplier', 'book', 'expected_delivery_date']

        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'book': forms.Select(attrs={'class': 'form-select'}),
            'expected_delivery_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control my-3'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Hidden('action', 'add_order'))  
        self.helper.add_input(Submit('submit', 'Create order', css_class="btn-green text-brown border-0 hover-shadow my-2"))

#_____________________________________________________________
class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Save Changes', css_class="btn-green text-brown border-0 hover-shadow my-2"))

#____________________________________________________________
#form that adds a new supplier to the database
class SupplierForm(forms.ModelForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='add_supplier')  

    class Meta:
        model = Supplier
        fields = ['name', 'email', 'phone', 'address']

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'email': forms.EmailInput(attrs={'class': 'form-control my-2'}),
            'phone': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'address': forms.Textarea(attrs={'class': 'form-control my-2', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Hidden('action', 'add_supplier')) 
        self.helper.add_input(Submit('submit', 'Add Supplier', css_class="btn-green text-brown border-0 hover-shadow my-2"))   

#___________________________________________________________
#for adding a new borrow to the database
class BorrowForm(forms.ModelForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='add_borrow')  

    class Meta:
        model = Borrow
        fields = ['borrower', 'book']

        widgets = {
            'borrower': forms.Select(attrs={'class': 'form-select my-2'}),
            'book': forms.Select(attrs={'class': 'form-select my-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Hidden('action', 'add_borrow'))
        self.helper.add_input(Submit('submit', 'Add Borrow', css_class="btn btn-outline-green"))

        # Filter borrowers to only show READER users
        self.fields['borrower'].queryset = Person.objects.filter(role=RoleName.READER)

#_____________________________________________________________
class ReviewForm(forms.ModelForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='add_review')
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=Review.RATING_CHOICES),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your review...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Hidden('action', 'add_review'))
        self.helper.add_input(Submit('submit', 'Submit Review', css_class="btn btn-outline-green"))


#_____________________________________________________________
class EventCreateForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'host', 'poster', 'description', 'event_price', 'audience',
            'location', 'start_datetime', 'end_datetime', 'nbr_reservations', 'event_type', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'host': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'poster': forms.ClearableFileInput(attrs={'class': 'form-control my-2'}),
            'description': forms.Textarea(attrs={'class': 'form-control my-2', 'rows': 3}),
            'event_price': forms.NumberInput(attrs={'class': 'form-control my-2'}),
            'audience': forms.Select(attrs={'class': 'form-select my-2'}),
            'location': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control my-2', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control my-2', 'type': 'datetime-local'}),
            'nbr_reservations': forms.NumberInput(attrs={'class': 'form-control my-2'}),
            'event_type': forms.Select(attrs={'class': 'form-select my-2'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Create Event', css_class="btn btn-success"))

#_____________________________________________________________
class EventEditForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'host', 'poster', 'description', 'event_price', 'audience',
            'location', 'start_datetime', 'end_datetime', 'nbr_reservations', 'event_type', 'is_public', 'is_canceled'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'host': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'poster': forms.ClearableFileInput(attrs={'class': 'form-control my-2'}),
            'description': forms.Textarea(attrs={'class': 'form-control my-2', 'rows': 3}),
            'event_price': forms.NumberInput(attrs={'class': 'form-control my-2'}),
            'audience': forms.Select(attrs={'class': 'form-select my-2'}),
            'location': forms.TextInput(attrs={'class': 'form-control my-2'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control my-2', 'type': 'datetime-local'}),
            'end_datetime': forms.DateTimeInput(attrs={'class': 'form-control my-2', 'type': 'datetime-local'}),
            'nbr_reservations': forms.NumberInput(attrs={'class': 'form-control my-2'}),
            'event_type': forms.Select(attrs={'class': 'form-select my-2'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_canceled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Save Changes', css_class="btn btn-outline-brown"))


