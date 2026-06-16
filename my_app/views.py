from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required(login_url='users:login')
def home_view(request):
    return render(request, 'my_app/home.html')