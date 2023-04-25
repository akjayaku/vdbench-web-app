import paramiko
import ping3
import subprocess
import re
import time
from .models import RemoteSystem
from django.shortcuts import get_object_or_404

def is_reachable(ip_address):
    timeout = 1
    response_time = ping3.ping(ip_address, timeout=timeout)
    if response_time is not None:
        return True
    return False

def execute(pk, cmd, timeout=10):
    try:
        remote_server = get_object_or_404(RemoteSystem, pk=pk)
        username = remote_server.username
        password = remote_server.password
        server_ip = remote_server.server_address
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_ip, username=username, password=password)
        output = "" 
        if type(cmd) == list:
           for c in cmd:
                stdin, stdout, stderr = ssh.exec_command(c,timeout=timeout)
                output = stdout.read().decode()
                print(output)
        else:
            stdin, stdout, stderr = ssh.exec_command(cmd,timeout=timeout)
            output = stdout.read().decode() 
        ssh.close()
    except Exception as e:
        print(e)
        return ""    
    return output
def is_vdbench_present(pk):
    cmd = """if test -d /root/VD; then echo "exist"; fi"""    
    output = execute(pk,cmd)
    if not output:
        cmd = "mkdir -p /root/VD"
        out = execute(pk,cmd) 
        cmd = "curl http://ndfc-web.cisco.com/vdbench/vdbench50407.zip -o /root/VD/vdbench.zip" 
        out = execute(pk,cmd, timeout=120)
        cmd = "unzip /root/VD/vdbench.zip -d  /root/VD/"
        out = execute(pk,cmd, timeout=120) 
def is_vdbench_running(pk):
    cmd = "ps aux | grep -v grep | grep  Vdbmain | head -n 1 |awk '{print$2}'"
    output = execute(pk,cmd)
    pids = output.splitlines()
    if pids:
        print("Vdbench is running, pids:", pids) 
        return True
    return False 
def set_hostname(pk):
    cmd = 'hostname'
    output = execute(pk,cmd)
    remote_server = get_object_or_404(RemoteSystem, pk=pk)
    remote_server.name = output 
    remote_server.save() 
def get_vdbench_intance(pk):
    cmd = "ps aux | grep -v grep | grep  Vdbmain | head -n 1 |awk '{print$2}'"
    output = execute(pk,cmd)
    pids = output.splitlines()
    return len(pids)
def stop_vdbench(pk):
    cmd = "ps aux | grep -v grep | grep  Vdbmain | head -n 1 |awk '{print$2}'"
    output = execute(pk,cmd)
    pids = output.splitlines()
    for pid in pids:
        output = execute(pk,"kill -9 %s"%(pid))
    output = execute(pk,cmd)
    pids = output.splitlines() 
    if pids:
        return False
    return True
def start_vdbench(pk):
    if is_vdbench_running(pk):
        ret = stop_vdbench(pk)
        if not ret:
            return False
    # run Vdbench command on remote server
    cmd = '/root/VD/vdbench -f /root/VD/config.txt -o /root/VD/output/ >/dev/null &'
    output = execute(pk,cmd)
    print("vdbench run debug" , output) 
    if is_vdbench_running(pk):
        print("vdbench started..")
        return True
    #print("sleeping 30 sec...")
    #time.sleep(1)
    if is_vdbench_running(pk):
        print("vdbench started..")
        return True
    return False
def get_graph_data(pk):
    metrics_stack = {'rdect':[], 'wrect': [], 'blocksize': [], 'timestamp': []}
    #cmd = "grep ''$(date -d '5 minutes ago' '+%H:%M')'' /root/VD/output/logfile.html | awk '{print}'"
    #cmd = """grep -E "$(date -d '10 minutes ago' '+%H:%M').*|$(date '+%H:%M')" /root/VD/output/logfile.html"""
    #cmd = """awk -v d="$(date '+%b %d, %Y')" '$0 ~ d {p=1} p' /root/VD/output/logfile.html"""
    cmd = """awk -v d="$(date -d '-10 min' '+%b %d, %Y %H:%M')" '$0 > d {p=1} p' /root/VD/output/logfile.html | tail -600"""
    output = execute(pk,cmd) 
    lines = re.findall(r'\d{2}:\d{2}:\d{2}\.\d{3}\s+\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+\s+\d+\.\d+',output)
    lines = sorted(lines)
    for line in lines:
        data = line.split()
        timestamp = data[0]
        iorate = data[2]
        mbps = data[3]
        blocksize = data[4]
        rdect = data[7]
        wrect = data[8]
        qdepth = data[12]
        metrics_stack['rdect'].append(rdect)
        metrics_stack['wrect'].append(wrect)
        metrics_stack['blocksize'].append(blocksize) 
        metrics_stack['timestamp'].append(timestamp[:-4]) 
    return metrics_stack 
    
def get_metrics(pk):
    cmd = "pgrep vdbench"
    output = execute(pk,cmd)
    pids = output.split()
    print(pids) 
    ret = {'pids': False, 'iosize': 0, 'iorate': 0, 'throughput': 0, 'readpct': 0,
        'writepct': 0, 'readect': 0 , 'writeect': 0, 'queue': 0, 'cpu': 0 }
    if not pids:
        return ret
    cmd = "tail -20 /root/VD/output/logfile.html"
    output = execute(pk,cmd)
    row_regex = re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d+)\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)$')

    # Extract the values from each data row using the regular expression
    rows = [row_regex.match(line) for line in output.split('\n')]

    # Convert the matched groups to a dictionary for each row
    data = []
    io_rates = []
    mb_sec = []
    avg_bytes_io = []
    r_resp = []
    w_resp = []
    que_depth = []
    cpu_usage = []
    r_pct = []
    for row in rows:
       if row is not None:
           row_dict = {}
           row_dict['time'] = row.group(1)
           row_dict['interval'] = int(row.group(2))
           row_dict['i/o rate'] = float(row.group(3))
           io_rates.append(row_dict['i/o rate'])
           row_dict['MB/sec'] = float(row.group(4))
           mb_sec.append(row_dict['MB/sec']) 
           row_dict['bytes/i/o'] = int(row.group(5))
           avg_bytes_io.append(row_dict['bytes/i/o']) 
           row_dict['pct read'] = float(row.group(6))
           r_pct.append(row_dict['pct read'])
           row_dict['resp time'] = float(row.group(7))
           row_dict['read resp time'] = float(row.group(8))
           r_resp.append(row_dict['read resp time'])
           row_dict['write resp time'] = float(row.group(9))
           w_resp.append(row_dict['write resp time'])
           row_dict['max read resp time'] = float(row.group(10))
           row_dict['max write resp time'] = float(row.group(11))
           row_dict['stddev resp time'] = float(row.group(12))
           row_dict['queue depth'] = float(row.group(13))
           que_depth.append(row_dict['queue depth']) 
           row_dict['cpu sys+u'] = float(row.group(14))
           cpu_usage.append(row_dict['cpu sys+u']) 
           row_dict['cpu sys'] = float(row.group(15))
           data.append(row_dict)
    # Print the data
    try:
        avg_io_rate = int(sum(io_rates) / len(io_rates))
    except:
        avg_io_rate = 0
    try:            
        avg_mb_sec = round(sum(mb_sec) / len(mb_sec), 2)
    except:
        avg_mb_sec = 0
    try: 
        avg_bytes_per_io = round((sum(avg_bytes_io)/ len(avg_bytes_io)/1000),2)
    except:
        avg_bytes_per_io  = 0
    try:
        avg_r_resp = round(sum(r_resp)/ len(r_resp), 2)
    except:
        avg_r_resp = 0
    try: 
        avg_w_resp = round(sum(w_resp)/ len(w_resp), 2)
    except:
        avg_w_resp = 0 
    try:
        avg_r_pct = round(sum(r_pct)/ len(r_pct),2)
        avg_que_depth = int(sum(que_depth)/ len(que_depth))
        avg_cpu_usage = round(sum(cpu_usage)/ len(cpu_usage),2)
    except:
        avg_r_pct = 0
        avg_que_depth = 0
        avg_cpu_usage = 0 
    ret = {'pids': pids, 'iosize': avg_bytes_per_io, 'iorate': avg_io_rate, 'throughput': avg_mb_sec, 'readpct': avg_r_pct,
        'writepct': 100.0-avg_r_pct, 'readect': avg_r_resp , 'writeect': avg_w_resp, 'queue': avg_que_depth, 'cpu': avg_cpu_usage }       
    return ret
def list_block_devices(serverobj):
    ssh_cmd = ['sshpass', '-p', '%s'%(serverobj.password), 'ssh', '-o', 'StrictHostKeyChecking=no',
              "%s@%s"%(serverobj.username,serverobj.server_address), 'lsblk', '-d', '-n', '-o', 'NAME,VENDOR,SIZE', '-e', '7,11']
    output = subprocess.check_output(ssh_cmd, universal_newlines=True)
    block_devices = output.strip().split('\n')
    context = {'block_devices': block_devices}
    return context
def get_os_verion(serverobj):
    ssh_cmd = ['sshpass', '-p', serverobj.password, 'ssh', '-o', 'StrictHostKeyChecking=no',
               f'{serverobj.username}@{serverobj.server_address}', 'cat /etc/*release']
    output = subprocess.check_output(ssh_cmd, stderr=subprocess.STDOUT).decode('utf-8')
    output = output.replace('\r', '').replace('\n', '')
    match = re.search(r'(?<=NAME=")([^"]*)(?=").*(?<=VERSION=")([^"]*)(?=")', output)
    if match:
        name = match.group(1).split()
        version = match.group(2)
        return name[0] +  ' ' + version

def get_kernal(serverobj):
    ssh_cmd = ['sshpass', '-p', serverobj.password, 'ssh', '-o', 'StrictHostKeyChecking=no',
                f'{serverobj.username}@{serverobj.server_address}', 'uname -a']

    output = subprocess.check_output(ssh_cmd, stderr=subprocess.STDOUT).decode('utf-8')
    return output

def get_systems(srv):
    context = {}
    context[srv] = {} 
    out = {}
    if not is_reachable(srv.server_address):
        return context 
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
    return context

def get_profile(profile):
    pass



