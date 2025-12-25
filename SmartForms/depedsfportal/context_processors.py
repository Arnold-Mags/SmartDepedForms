from .models import School


def school_context(request):
    """
    Make the School object available to all templates.
    Assumes there is at least one school record (or singleton).
    """
    school = School.objects.first()
    return {"school": school}
