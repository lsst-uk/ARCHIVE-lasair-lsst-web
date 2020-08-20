import lasair.settings

def dev(request):
    """dev.

    Args:
        request:
    """
    return {'WEB_DOMAIN': lasair.settings.WEB_DOMAIN}