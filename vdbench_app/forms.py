from django import forms
from .models import RemoteSystem
from django.forms.widgets import CheckboxSelectMultiple


class RemoteSystemForm(forms.ModelForm):
    class Meta:
        model = RemoteSystem
        fields = ['server_address', 'username', 'password']

class VdbenchProfileForm1(forms.Form):
    block_device = forms.CharField(max_length=50)
    transfer_size = forms.IntegerField()
    io_rate = forms.IntegerField()
    elapsed_time = forms.IntegerField()
    interval = forms.IntegerField()

class VdbenchProfileForm2(forms.ModelForm):
    class Meta:
        model = RemoteSystem
        fields = ['block_device_list', 'profile']

class VdbenchProfileForm(forms.Form):
    PROFILE_TYPES = [
        ('Latency', 'Latency Test'),
        ('Throughput', 'Throughput Test'), 
        ('IOPs', 'IOPs Test'), 
    ]
    TEST_TYPES = [
        ('Readonly', 'Readonly'),
        ('Writeonly', 'Writeonly'),
        ('ReadWrite', 'ReadWrite'), 
    ]
    SEEK_TYPES = [
        ('Sequential', 'Sequential'),
        ('Random', 'Random'),
    ]
    profile = forms.ChoiceField(choices=PROFILE_TYPES, widget=forms.Select)
    test_type = forms.ChoiceField(choices=TEST_TYPES, widget=forms.Select) 
    seek_type = forms.ChoiceField(choices=SEEK_TYPES, widget=forms.Select) 
    elapsed_time = forms.IntegerField(min_value=1, max_value=1000000, required=True, initial=60)
    interval = forms.IntegerField(min_value=1, max_value=1000000, required=True, initial=1)
    block_devices = forms.MultipleChoiceField(choices=[], required=True, widget=forms.SelectMultiple)
    def __init__(self, *args, **kwargs):
        block_devices = kwargs.pop('block_devices')
        super().__init__(*args, **kwargs)
        self.fields['block_devices'].choices = [(bd, bd) for bd in block_devices]
        self.fields['block_devices'].widget.attrs['size'] = len(block_devices)