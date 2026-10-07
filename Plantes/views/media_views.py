from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.static import serve


@login_required
def serve_media(request, path):

    # Photos de plantes et d'espèces : réservées aux utilisateurs connectés.
    # django.views.static.serve refuse les chemins qui remontent hors de MEDIA_ROOT.
    return serve(request, path, document_root=settings.MEDIA_ROOT)
