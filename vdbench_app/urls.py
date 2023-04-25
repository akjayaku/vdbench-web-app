from django.urls import path
from .views import *

urlpatterns = [
    path('', Home.as_view() , name='home'),  
    path('list_remote_systems/', list_remote_systems, name='list_remote_systems'),
    path('add_remote_system/', add_remote_system, name='add_remote_system'),
    path('edit-remote-system/<int:pk>/', edit_remote_system, name='edit_remote_system'),    
    path('delete-remote-system/<int:pk>/', delete_remote_system, name='delete_remote_system'),
    path('modify_remote_systems', modify_remote_systems, name='modify_remote_systems'), 
    path('config_vdbench/<int:pk>/', config_vdbench, name='config-vdbench'),  
    path('vdbench/<int:pk>/', VdbenchView.as_view(), name='vdbench-monitor'),
    path('start-vdbench/<int:pk>/', VdbenchRun.as_view(), name='vdbench-start'), 
    path('stop-vdbench/<int:pk>/', VdbenchStop.as_view(), name='vdbench-stop'),  
    path('log_view/<int:pk>/', log_view, name='log_view'),  
    path('home', Home.as_view(), name='home'), 
    path('home/<int:pk>/', Home.as_view(), name='device-home'), 
    path('vdbench-graph/<int:pk>/', VdbenchGraph.as_view(), name='vdbench-graph'),
]
