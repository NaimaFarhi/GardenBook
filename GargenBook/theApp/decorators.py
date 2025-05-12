from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from .models import Borrow, Person


def role_required(allowed_roles):
  """
  Allows access only to users with specified roles.
  Usage: @role_required(['Admin', 'Staff'])
  """
  def decorator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
      if hasattr(request.user, 'role') and request.user.role in allowed_roles:
        return view_func(request, *args, **kwargs)
      messages.warning(request, "Access denied: insufficient permissions.")
      return redirect('home')  # Or a 403 page
    return wrapper
  return decorator


def owner_only(model, lookup_kwarg='pk'):
  """
  Allows access only if the user is the owner of the object.
  Usage: @owner_only(Person)
  """
  def decorator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
      obj = get_object_or_404(model, id=kwargs[lookup_kwarg])
      if obj.id == request.user.id:
        return view_func(request, *args, **kwargs)
      return HttpResponseForbidden("Access denied: not the object owner.")
    return wrapper
  return decorator


def prevent_duplicate_borrow():
  """
  Prevents a user from borrowing the same book twice if it's not returned.
  Usage: @prevent_duplicate_borrow()
  """
  def decorator(view_func):
    @wraps(view_func)
    def wrapper(request, book_id, *args, **kwargs):
      if Borrow.objects.filter(borrower=request.user, book_id=book_id, returned=False).exists():
        messages.info(request, "You have already borrowed this book.")
        return redirect('book-detail', pk=book_id)
      return view_func(request, book_id, *args, **kwargs)
    return wrapper
  return decorator


def prevent_duplicate_reservation():
  """
  Prevents a user from reserving a book they already borrowed and haven't returned.
  Usage: @prevent_duplicate_reservation()
  """
  def decorator(view_func):
    @wraps(view_func)
    def wrapper(request, book_id, *args, **kwargs):
      if Borrow.objects.filter(person=request.user, book_id=book_id, returned=False, is_fine_paid=False).exists():
        messages.info(request, "You already borrowed this book and haven't returned it.")
        return redirect('book-detail', pk=book_id)
      return view_func(request, book_id, *args, **kwargs)
    return wrapper
  return decorator

