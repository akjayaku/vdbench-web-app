import argparse
import inspect
import json
import logging
import multiprocessing
import os
import paramiko
import random
import requests
import shlex
import subprocess
import sys
import tempfile
import time
from gevent.pool import Pool
from datetime import datetime
from multiprocessing import Process, freeze_support, Manager, cpu_count
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import RemoteSystem
from .forms import RemoteSystemForm, VdbenchProfileForm
from .utils import *  
from django.views.generic.base import TemplateView
from .models import VdbenchResult
from django.http import StreamingHttpResponse
from django.views.generic.base import TemplateView
from django.views.decorators import gzip

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required
def log_view(request, pk):
    remote_server = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)
    username = remote_server.username
    password = remote_server.password
    server_ip = remote_server.server_address 

    def stream_response():
        ssh_cmd = f'sshpass -p {password} ssh {username}@{server_ip} "tail -f /root/VD/output/localhost.html"'
        proc = subprocess.Popen(ssh_cmd, shell=True, stdout=subprocess.PIPE)

        for line in iter(proc.stdout.readline, b''):
            yield line.decode()
        proc.kill()

    response = StreamingHttpResponse(stream_response(), content_type='text/plain')
    #response['Content-Encoding'] = 'gzip'
    response['Cache-Control'] = 'no-cache'
    return response

class VdbenchRun(LoginRequiredMixin, TemplateView):
    template_name = "vdbench_app/vdbench_run.html"
    def post(self, request, *args, **kwargs):
        # connect to remote server via SSH
        pk = kwargs['pk']
        remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user) 
        print("Hello vdbench...")
        # kill vdbench instances
        status = start_vdbench(pk)
        print("Hello status", status)
        return self.render_to_response({"status": status, 'pk': pk, 'system': remote_system.server_address}) 
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)  
        try:
            config = remote_system.vdbench_config.splitlines()
        except:
            config = [] 
        return self.render_to_response({'pk': pk, 'system': remote_system.server_address, 'config': config }) 
class VdbenchStop(LoginRequiredMixin, TemplateView):
    template_name = "vdbench_app/vdbench_stop.html"
    def post(self, request, *args, **kwargs):
        # connect to remote server via SSH
        pk = kwargs['pk']
        remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user) 
        # kill vdbench instances
        status = stop_vdbench(pk)
        return self.render_to_response({"status": status, 'pk': pk, 'system': remote_system.server_address})
    def get(self, request, *args, **kwargs):
        pk = kwargs['pk']
        remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)  
        return self.render_to_response({'pk': pk, 'system': remote_system.server_address}) 
class VdbenchView(LoginRequiredMixin, TemplateView):
    template_name = "vdbench_app/vdbench_monitor.html"
    #template_name = "vdbench_app/home.html" 
    def get(self, request, *args, **kwargs):
        # connect to remote server via SSH
        pk = kwargs['pk']
        remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user) 
        metrics_data = get_metrics(pk)
        if metrics_data['pids']:
            metrics_data['status'] = f"Running, PIDs are {','.join(metrics_data['pids'])}"
        # render template with results
        metrics_data['server_ip'] = remote_system.server_address
        #metrics_data['metrics'] = True 
        return self.render_to_response(metrics_data)

class VdbenchGraph(LoginRequiredMixin, TemplateView):
    template_name = "vdbench_app/vdbench_graph.html"

    def get(self, request, *args, **kwargs):
        # connect to remote server via SSH
        pk = kwargs['pk']
        metrics_data = {} 
        remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user ) 
        metrics_data['server_ip'] = remote_system.server_address
        _data = get_graph_data(pk)
        metrics_data['timestamp'] = _data['timestamp'] 
        metrics_data['rdect'] = _data['rdect']
        metrics_data['wrect'] = _data['wrect'] 
        metrics_data['blocksize'] = _data['blocksize'] 
        return self.render_to_response(metrics_data)
@login_required
def config_vdbench(request, pk):
    remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)
    remote_server = remote_system.server_address
    username = remote_system.username
    password = remote_system.password 
    block_devices = [i.replace("[","").replace("]","") for i in remote_system.block_device_list.split(',')]
    remote_path = '/root/VD/config.txt'
    if request.method == 'POST':
        form = VdbenchProfileForm(request.POST,block_devices=block_devices)
        if form.is_valid():
            block_devices = form.cleaned_data['block_devices']
            vd_profile = form.cleaned_data['profile'] 
            test_type = form.cleaned_data['test_type']
            seek_type = form.cleaned_data['seek_type'] 
            if test_type == 'Readonly':
                rdpct = 100
                rhpct = 10
                whpct = 0
            elif test_type == 'Writeonly':
                rdpct = 0
                rhpct = 0
                whpct = 10
            else:
                rdpct = 50
                rhpct = 10
                whpct = 10
            seekpct = 100 
            if seek_type == 'Sequential':
                seekpct = 0
            if vd_profile == 'IOPs':
                transfer_size = '4K'
                io_rate = 'max'
                threads = 256
            elif vd_profile == 'Throughput':
                transfer_size = '64K'
                io_rate = 'max'
                threads = 64
            elif vd_profile == 'Latency':
                transfer_size = '4K'
                io_rate = 'max'
                threads = 1
            elapsed_time = form.cleaned_data['elapsed_time']
            interval = form.cleaned_data['interval']

            # Generate the Vdbench profile file
            profile = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            i=1
            temp_list = []
            for device in block_devices:
                device = device.replace("'",'')
                sd,vendor,size = device.split()
                profile.write(f"sd=sd{i},lun=/dev/{sd},openflags=o_direct,threads={threads},size={size},hitarea=4m,align=512\n")
                temp_list.append(f"wd=wd{i},sd=sd{i},xfersize={transfer_size},rdpct={rdpct},rhpct={rhpct},whpct={whpct},seekpct={seekpct}\n")
                i += 1
            [profile.write(i) for i in temp_list]    
            profile.write(f"rd=run1,wd=wd*,iorate={io_rate},elapsed={elapsed_time}m,interval={interval}")
            profile.seek(0)
            content = profile.read()
            remote_system.vdbench_config = content  
            content = content.splitlines() 
            profile.close()
            remote_system.save()
            #ssh_command = f'sshpass -p "{password}" ssh {username}@{remote_server} "vdbench -f {shlex.quote(profile.name)}"'
            scp_command = f'sshpass -p "{password}" scp {shlex.quote(profile.name)} {username}@{remote_server}:{shlex.quote(remote_path)}'
            result = subprocess.run(scp_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
  
            # Delete the temporary profile file
            os.unlink(profile.name)
            
            # Return the Vdbench results to the user
            return render(request, 'vdbench_app/vdbench.html', {'form': form, 'status': 'SUCCESS', 'pk': pk, 'system': remote_server,'filecontent': content })
    else:
        form = VdbenchProfileForm(block_devices=block_devices)

    return render(request, 'vdbench_app/vdbench.html', {'form': form, 'system': remote_server, 'pk': pk})
@login_required 
def modify_remote_systems(request):
    # Get a list of all remote systems
    remote_systems = RemoteSystem.objects.filter(owner=request.user)
    return render(request, 'vdbench_app/modify_remote_systems.html', {'remote_systems': remote_systems}) 

@login_required    
def list_remote_systems(request):
    pool = Pool(50)
    # Get a list of all remote systems
    remote_systems = RemoteSystem.objects.filter(owner=request.user)
    results = pool.map(get_systems, remote_systems)
    context = {}
    [context.update(d) for d in results]
    print(context)
    """
    context = {}
    out = {}
    for srv in remote_systems:
        if not is_reachable(srv.server_address):
            continue
        try:
            out = list_block_devices(srv)
            out['total_devices'] = len(out['block_devices'])
            out['os'] = get_os_verion(srv)
            srv.block_device_list = [i for i in out['block_devices']]
            srv.save()
            context[srv] = out
        except Exception as e:
            print(e)
            context[srv] = {}
    # Render a template with the remote system list
    """
    return render(request, 'vdbench_app/list_remote_systems.html', {'remote_systems': remote_systems, 'context': context})

@login_required
def add_remote_system(request):
    if request.method == 'POST':
        # Create a form instance and populate it with data from the request
        form = RemoteSystemForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.owner = request.user
            # Save the new remote system and redirect to the list of remote systems
            instance.save()
            set_hostname(instance.id)
            is_vdbench_present(instance.id)
            return redirect('home')
        else:
            return redirect('home') 
    else:
        # Render a blank form
        form = RemoteSystemForm()

    return render(request, 'vdbench_app/add_remote_system.html', {'form': form})
@login_required
def edit_remote_system(request, pk):
    remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = RemoteSystemForm(request.POST, instance=remote_system)
        if form.is_valid():
            form.save()
            set_hostname(pk) 
            return redirect('modify_remote_systems')
    else:
        form = RemoteSystemForm(instance=remote_system)
    return render(request, 'vdbench_app/edit_remote_systems.html', {'form': form, 'remote_system': remote_system})

@login_required
def delete_remote_system(request, pk):
    remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)
    if request.method == 'POST':
        remote_system.delete()
        return redirect('home')
    return render(request, 'vdbench_app/delete_remote_systems.html', {'remote_system': remote_system})

class Home(LoginRequiredMixin, TemplateView):
    template_name = "vdbench_app/home.html"
    def post(self, request, *args, **kwargs):
        remote_systems = RemoteSystem.objects.filter(owner=request.user)
        pk = False
        vdstatus = 'Not Running' 
        if 'pk' in kwargs:
            pk = kwargs['pk']
        if pk:
            remote_systems = RemoteSystem.objects.filter(owner=request.user)
            remote_system = get_object_or_404(RemoteSystem, pk=pk, owner=request.user)
            context = get_systems(remote_system)
            metrics_data = get_metrics(pk)
            metrics_graph = {} 
            _data = get_graph_data(pk)
            metrics_graph['timestamp'] = _data['timestamp'] 
            metrics_graph['rdect'] = _data['rdect']
            metrics_graph['wrect'] = _data['wrect'] 
            metrics_graph['blocksize'] = _data['blocksize'] 
            instance_count = get_vdbench_intance(pk)
            if instance_count:
                vdstatus = 'Running' 
            return self.render_to_response({'devices': remote_systems, 'selected_device': remote_system, 'context': context ,\
                 'metrics': metrics_data, 'graph': metrics_graph, 'pk': pk, 'vdstatus': vdstatus, 'instances': instance_count})
        return self.render_to_response({'devices': remote_systems, 'vdstatus': vdstatus})
    def get(self, request, *args, **kwargs):
        remote_systems = RemoteSystem.objects.filter(owner=request.user)
        return self.render_to_response({'devices': remote_systems})