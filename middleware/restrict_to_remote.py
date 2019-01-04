from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden


def allow_anyone(view_func):
    view_func.allow_anyone = True
    return view_func


def allow_build(view_func):
    view_func.allow_build = True
    return view_func


def sysadmin_only(view_func):
    view_func.sysadmin_only = True
    return view_func


def _in_group(user, group):
    try:
        user.groups.get(name=group)
        return True
    except ObjectDoesNotExist:
        return False
