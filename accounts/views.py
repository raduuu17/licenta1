import base64
import io

import qrcode
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.http import JsonResponse
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import CustomUserCreationForm, UserPreferenceForm
from .models import User, UserPreference

class SignUpView(SuccessMessageMixin, CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('set_preferences')
    template_name = 'accounts/signup.html'
    success_message = "Your account was created successfully! Please set your preferences."
    
    def form_valid(self, form):
        # Save the user object from the form
        valid = super().form_valid(form)
        
        # Log the user in immediately after signup
        login(self.request, self.object)
        
        # Create empty preference object for the user
        UserPreference.objects.create(user=self.object)
        
        # Add a success message
        messages.success(self.request, self.success_message)
        
        # Return the valid form response
        return valid

@login_required
def set_preferences(request):
    try:
        preferences = request.user.preferences
    except UserPreference.DoesNotExist:
        preferences = UserPreference.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            return redirect('hotel_recommendations')
    else:
        form = UserPreferenceForm(instance=preferences)
    
    return render(request, 'accounts/set_preferences.html', {'form': form})

@login_required
def user_profile(request):
    return render(request, 'accounts/profile.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('home')

class UpdateProfileView(SuccessMessageMixin, UpdateView):
    model = User
    fields = ['username', 'email', 'phone_number', 'profile_picture']
    template_name = 'accounts/update_profile.html'
    success_url = reverse_lazy('profile')
    success_message = "Your profile was updated successfully!"
    
    def get_object(self):
        return self.request.user

class UpdatePreferencesView(SuccessMessageMixin, UpdateView):
    model = UserPreference
    form_class = UserPreferenceForm
    template_name = 'accounts/set_preferences.html'
    success_url = reverse_lazy('profile')
    success_message = "Your preferences were updated successfully!"
    
    def get_object(self):
        try:
            return self.request.user.preferences
        except UserPreference.DoesNotExist:
            return UserPreference.objects.create(user=self.request.user)
    
    def post(self, request, *args, **kwargs):
        """Override post to explicitly handle the form submission"""
        self.object = self.get_object()
        form = self.get_form()
        
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        try:
            self.object = form.save()
            messages.success(self.request, self.success_message)
            return redirect(self.success_url)
        except Exception as e:
            print(f"Error saving preferences: {str(e)}")
            messages.error(self.request, f"Error saving preferences: {str(e)}")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        print(f"Form validation errors: {form.errors}")
        messages.error(self.request, "There was an error with your form. Please check the fields below.")
        return super().form_invalid(form)

def _safe_next_url(request, fallback='/admin/'):
    """Return the ?next= URL if it is safe to redirect to, else the fallback."""
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return fallback


def _qr_code_data_uri(text):
    """Render a QR code for the given text as a base64 PNG data URI."""
    image = qrcode.make(text)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


@login_required
def two_factor_setup(request):
    """Enroll a staff user into 2FA: show a QR code and confirm the first token."""
    if not request.user.is_staff:
        messages.error(request, "Two-factor authentication is only available for staff accounts.")
        return redirect('home')

    # Already enrolled - verify instead of re-enrolling
    if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
        return redirect('two_factor_verify')

    # Reuse the pending (unconfirmed) device so the QR code stays stable across reloads
    device, _ = TOTPDevice.objects.get_or_create(
        user=request.user,
        confirmed=False,
        defaults={'name': 'Google Authenticator'},
    )

    if request.method == 'POST':
        token = request.POST.get('token', '').strip().replace(' ', '')
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            otp_login(request, device)
            messages.success(request, "Two-factor authentication has been enabled for your account.")
            return redirect(_safe_next_url(request))
        messages.error(request, "Invalid code. Make sure you scanned the QR code and try again.")

    context = {
        'qr_code': _qr_code_data_uri(device.config_url),
        'secret_key': base64.b32encode(device.bin_key).decode(),
        'next': request.GET.get('next', ''),
    }
    return render(request, 'accounts/two_factor_setup.html', context)


@login_required
def two_factor_verify(request):
    """Ask for the 6-digit code from the authenticator app."""
    if not request.user.is_staff:
        messages.error(request, "Two-factor authentication is only available for staff accounts.")
        return redirect('home')

    devices = list(TOTPDevice.objects.filter(user=request.user, confirmed=True))
    if not devices:
        return redirect('two_factor_setup')

    if request.method == 'POST':
        token = request.POST.get('token', '').strip().replace(' ', '')
        for device in devices:
            if device.verify_token(token):
                otp_login(request, device)
                return redirect(_safe_next_url(request))
        messages.error(request, "Invalid or expired code. Please try again.")

    return render(request, 'accounts/two_factor_verify.html', {'next': request.GET.get('next', '')})


@login_required
def toggle_theme(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        theme = request.POST.get('theme')
        if theme in ['light', 'dark', 'system']:
            try:
                user_pref = request.user.preferences
            except UserPreference.DoesNotExist:
                user_pref = UserPreference.objects.create(user=request.user)
            
            user_pref.theme_preference = theme
            user_pref.save()
            return JsonResponse({'success': True, 'theme': theme})
        
    return JsonResponse({'success': False}, status=400)