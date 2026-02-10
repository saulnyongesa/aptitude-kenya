from django.shortcuts import render
from .models import SiteStatistic, ContactMessage
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .models import User

def index(request):
    # Fetch stats from the SiteStatistic model (Singleton-style)
    stats = SiteStatistic.objects.first()
    
    context = {
        'tutor_count': stats.tutor_count if stats else 0,
        'student_count': stats.student_count if stats else 0,
        'classroom_count': stats.classroom_count if stats else 0,
        'exam_count': stats.exam_count if stats else 0,
    }
    return render(request, 'index.html', context)

def send_message(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        
        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message_text
        )
        return JsonResponse({'message': 'Thank you! Your message has been received.'})
    return JsonResponse({'message': 'Invalid request'}, status=400)

def auth_view(request):
    if request.method == 'POST':
        # Check if it's a Register or Login attempt based on the 'role' field presence
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')  # Only present in Register mode

        if role:  # --- REGISTRATION LOGIC ---
            confirm_password = request.POST.get('confirm_password')
            
            if password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect('auth_page')

            if User.objects.filter(email=email).exists():
                messages.error(request, "A user with this email already exists.")
                return redirect('auth_page')

            # Create the user
            user = User.objects.create_user(
                username=email.split('@')[0], 
                email=email, 
                password=password
            )
            
            # Set Role
            if role == 'tutor':
                user.is_tutor = True
                user.is_student = False
            else:
                user.is_tutor = False
                user.is_student = True
            
            user.save()
            login(request, user)
            messages.success(request, f"Welcome to Aptitude Kenya, {role}!")
            return redirect('index')

        else:  # --- LOGIN LOGIC ---
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, "Invalid email or password.")

    return render(request, 'registration/login.html')

def logout_view(request):
    logout(request)
    return redirect('index')