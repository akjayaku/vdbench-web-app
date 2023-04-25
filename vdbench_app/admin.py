from django.contrib import admin
from .models import RemoteSystem, VdbenchResult

class RemoteSystemAdmin(admin.ModelAdmin):
    list_display = ('name', 'server_address', 'username','password','block_devices', 'profile')
class VdbenchResultAdmin(admin.ModelAdmin):
    list_display = ('output', 'timestamp')
admin.site.register(RemoteSystem, RemoteSystemAdmin)
admin.site.register(VdbenchResult,VdbenchResultAdmin)