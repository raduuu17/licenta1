from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    def __str__(self):
        return self.username

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    # Preferences that match with HotelAmenity
    wifi = models.BooleanField(default=False)
    parking = models.BooleanField(default=False)
    pool = models.BooleanField(default=False)
    spa = models.BooleanField(default=False)
    gym = models.BooleanField(default=False)
    restaurant = models.BooleanField(default=False)
    room_service = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=False)
    
    # Location preferences
    preferred_city = models.CharField(max_length=100, blank=True)
    preferred_district = models.CharField(max_length=100, blank=True)
    
    # Price range preferences
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Star rating preference
    min_star_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    
    # Additional preferences
    prefer_pet_friendly = models.BooleanField(default=False)
    prefer_family_friendly = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s preferences"