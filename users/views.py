from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistrationStep1Form, RegistrationStep2Form
from .models import User
from django.http import HttpResponse

def check_gamer_tag(request):
    gamer_tag = request.GET.get('gamer_tag', '').strip()
    if not gamer_tag:
        return HttpResponse('<div style="color: #94a3b8; margin-bottom: 1rem;">Enter a gamer tag to continue.</div>')
    
    if User.objects.filter(gamer_tag=gamer_tag).exists():
        return HttpResponse('<div style="color: #ef4444; margin-bottom: 1rem;">This Gamer Tag is already taken.</div>')
    
    # If unique, show the rest of the form
    html = f'''
        <div id="additional-fields" style="margin-top: 1.5rem; border-top: 1px solid #334155; padding-top: 1.5rem;">
            <p style="color: #22c55e; margin-bottom: 1rem;">✔ Gamer Tag "{gamer_tag}" is available!</p>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label for="id_full_name" style="display: block; margin-bottom: 0.5rem; color: #94a3b8;">Full Name</label>
                <input type="text" name="full_name" id="id_full_name" required 
                    style="width: 100%; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid #334155; background: #0f172a; color: #f8fafc; box-sizing: border-box;">
            </div>
            <div class="form-group" style="margin-bottom: 1rem;">
                <label for="id_county" style="display: block; margin-bottom: 0.5rem; color: #94a3b8;">County</label>
                <input type="text" name="county" id="id_county" required 
                    style="width: 100%; padding: 0.75rem; border-radius: 0.5rem; border: 1px solid #334155; background: #0f172a; color: #f8fafc; box-sizing: border-box;">
            </div>
            <button type="submit" 
                style="width: 100%; padding: 0.75rem; background: #38bdf8; color: #0f172a; border: none; border-radius: 0.5rem; font-weight: bold; cursor: pointer; transition: background 0.3s; margin-top: 1rem;">
                Complete Registration
            </button>
        </div>
    '''
    return HttpResponse(html)

def register_view(request):
    if request.method == 'POST':
        form = RegistrationStep1Form(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password1')
            user.set_password(password)
            user.username = user.email 
            user.save()
            login(request, user)
            messages.success(request, "Step 1 complete! Please provide your gamer tag and details.")
            return redirect('register_step2')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = RegistrationStep1Form()
    return render(request, 'users/register.html', {'form': form, 'step': 1})

@login_required
def register_step2_view(request):
    if request.method == 'POST':
        form = RegistrationStep2Form(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            from .models import PersonalProfile
            PersonalProfile.objects.get_or_create(user=user)
            messages.success(request, f"Registration complete! Welcome, {request.user.gamer_tag}!")
            return redirect('profile')
        else:
            # If the form is invalid (e.g. gamer_tag became taken between check and submit)
            # we should still show the step 2 page.
            messages.error(request, "Something went wrong. Please check your gamer tag again.")
    else:
        form = RegistrationStep2Form(instance=request.user)
    return render(request, 'users/register_step2.html', {'form': form, 'step': 2})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {user.username}.")
                return redirect('profile')
            else:
                messages.error(request, "Invalid email or PIN.")
        else:
            messages.error(request, "Invalid email or PIN.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

@login_required
def profile_view(request):
    return render(request, 'users/profile.html', {'user': request.user})
