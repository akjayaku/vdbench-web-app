from django.db import models
from accounts.models import CustomUser


class RemoteSystem(models.Model):
    PROFILE_TYPES = [
        ('Latency', 'Latency Test'),
        ('Throughput', 'Throughput Test'), 
        ('IOPs', 'IOPs Test'), 
    ]
    name = models.CharField(max_length=255,unique=True)
    server_address = models.CharField(max_length=255,unique=True)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    block_device_list = models.TextField(default='')
    profile = models.CharField(max_length = 100, choices = PROFILE_TYPES, default = 'Latency')
    vdbench_config = models.CharField(max_length=25500) 
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='Owner')
    @property
    def block_devices(self):
        return self.block_device_list.split(',')

    @block_devices.setter
    def block_devices(self, value):
        self.block_device_list = ','.join(value)
    def __str__(self):
        return self.name
class VdbenchResult(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    output = models.TextField()
    