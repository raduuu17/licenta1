from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.http import JsonResponse

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