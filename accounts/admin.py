from django.contrib import admin

# Register your models here.
from .models import *

class CustomUserManagerAdmin(admin.ModelAdmin):
    list_display = ('username')
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name')
admin.site.register(CustomUser,CustomUserAdmin)
