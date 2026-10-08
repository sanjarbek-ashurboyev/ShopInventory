"""Two roles. Owners see purchase prices and profit and manage stock; sellers scan and sell.

Anyone who is not an owner is a seller, so a newly created account starts with the smaller role.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission

OWNERS_GROUP = 'owners'


def is_owner(user):
    if not (user and user.is_authenticated):
        return False
    # Asked by several serializers per response; one query per request is enough.
    if not hasattr(user, '_is_shop_owner'):
        user._is_shop_owner = user.is_superuser or user.groups.filter(name=OWNERS_GROUP).exists()
    return user._is_shop_owner


class IsOwner(BasePermission):
    message = _('Only the shop owner can do this.')

    def has_permission(self, request, view):
        return is_owner(request.user)
