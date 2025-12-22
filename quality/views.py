from django.http import HttpResponse

def home(request):
    return HttpResponse("Quality app funcionando correctamente ✅")

