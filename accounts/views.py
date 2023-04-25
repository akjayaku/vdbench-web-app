from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView
from .forms import LoginForm

class LoginView(FormView):
    form_class = LoginForm
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            print("here")
            login(self.request, user)
            return super().form_valid(form)
        else:
            return redirect('login')

class LogoutView(LoginRequiredMixin, RedirectView):
    url = reverse_lazy('home')
    def get(self, request, *args, **kwargs):
        logout(request)
        return super().get(request, *args, **kwargs)
