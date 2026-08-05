from django.contrib.auth.models import User, auth
from django.shortcuts import render, redirect

# Create your views here.
def home(request):
    return render(request, 'core/home.html', {
        'title': 'Home'
    })

def signin(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        
        user_credentials = auth.authenticate(username=username, password=password)
        if user_credentials is not None:
            auth.login(request, user_credentials)
            print('Login succesfully.')
            return redirect('core:home')
        else:
            print('Invalid credentials.')
            return redirect('core:signin')
        
    return render(request, 'core/signin.html', {
        'title': 'Signin'
    })

def signup(request):
    if request.method == "POST":
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        if password == confirm_password:
            if User.objects.filter(email=email).exists():
                print('Email already exists.')
                return redirect('core:signup')
            elif User.objects.filter(username=username).exists():
                print('Username already exists.')
                return redirect('core:signup')
            else:
                new_user = User.objects.create_user(first_name=first_name, last_name=last_name, username=username, email=email, password=password)
                new_user.save()
                user_credentials = auth.authenticate(username=username, password=password)
                auth.login(request, user_credentials)
                print('Account created succesfully!')
                return redirect('core:home')
        else:
            print('Passwords don\'t match.')
            return redirect('core:signup')
    return render(request, 'core/signup.html', {
        'title': 'Signup'
    })

def signout(request):
    auth.logout(request)
    print('Logout succesfully.')
    return  redirect('core:signin')
