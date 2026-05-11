from rest_framework.permissions import BasePermission
from .models import Requests

class IsParent(BasePermission):
    """
    Custom permission to allow only parents to access a view.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or hasattr(request.user, "Parent"))


class IsBabysitter(BasePermission):
    """
    Custom permission to allow only babysitters to access a view.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or hasattr(request.user, "Babysitter"))

    
def check_parent_approved_by_babysitter(babysitter, parent):
    """
    Check if there is an approved request between the parent and babysitter.
    """
    try:
        Requests.objects.get(babysitter=babysitter, family=parent, status='approved', is_active=True)
        return True
    except Requests.DoesNotExist:
        return False