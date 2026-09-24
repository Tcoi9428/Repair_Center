from .catalog import CATALOGS

def navigation(request):
    return {'navigation_catalogs': [c for c in CATALOGS if request.user.is_authenticated and request.user.has_perm(c.permission('view'))]}

