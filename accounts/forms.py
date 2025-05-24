from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserPreference

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'phone_number', 'profile_picture')
        
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        exclude = ('user',)
        widgets = {
            'min_price': forms.NumberInput(attrs={'min': 0, 'step': 10}),
            'max_price': forms.NumberInput(attrs={'min': 0, 'step': 10}),
            'min_star_rating': forms.NumberInput(attrs={'min': 1, 'max': 5, 'step': 1}),
        }
        labels = {
            'wifi': 'Wi-Fi',
            'parking': 'Free Parking',
            'pool': 'Swimming Pool',
            'spa': 'Spa & Wellness',
            'gym': 'Fitness Center',
            'restaurant': 'On-site Restaurant',
            'room_service': 'Room Service',
            'air_conditioning': 'Air Conditioning',
            'preferred_city': 'Preferred City',
            'preferred_district': 'Preferred District/Area',
            'min_price': 'Minimum Price per Night',
            'max_price': 'Maximum Price per Night',
            'min_star_rating': 'Minimum Star Rating',
            'prefer_pet_friendly': 'Pet-Friendly Hotels',
            'prefer_family_friendly': 'Family-Friendly Hotels',
        }