from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include(('users.urls', "users"), namespace="users")), 
    path('my_app/', include(('my_app.urls', "users"), namespace="my_app")),
]