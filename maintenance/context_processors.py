def navigation(request):
    authenticated = request.user.is_authenticated
    return {
        'can_view_technology_cards': authenticated and request.user.has_perm('maintenance.view_technologycard'),
    }
