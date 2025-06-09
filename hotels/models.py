from django.db import models
from django.conf import settings

class Hotel(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)
    star_rating = models.PositiveSmallIntegerField(default=3)
    image = models.ImageField(upload_to='hotel_images/', blank=True, null=True)  
    is_pet_friendly = models.BooleanField(default=False)
    is_family_friendly = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_amenities(self):
        return self.amenities.all()
    
    def main_image(self):
        if self.image:
            return self.image.url
        
        first_image = self.images.first()
        if first_image:
            return first_image.image.url
        
        return None
    
    def match_score(self, user_preferences):
        required_amenities_score = 0
        required_amenities_count = 0
        bonus_score = 0
        max_score = 100
        
        amenities = self.amenities.all()
        amenity_names = [amenity.name.lower() for amenity in amenities]
        
        user_amenity_prefs = {
            'wifi': user_preferences.wifi,
            'parking': user_preferences.parking,
            'pool': user_preferences.pool,
            'spa': user_preferences.spa,
            'gym': user_preferences.gym,
            'restaurant': user_preferences.restaurant,
            'room_service': user_preferences.room_service,
            'air_conditioning': user_preferences.air_conditioning,
        }
        
        for amenity_name, is_preferred in user_amenity_prefs.items():
            if is_preferred:
                required_amenities_count += 1
        
        if required_amenities_count == 0:
            base_score = 70  
            bonus_amenities = min(len(amenity_names), 8)  
            bonus_score = bonus_amenities * 3  
            
            location_bonus = 0
            if user_preferences.preferred_city and self.city.lower() == user_preferences.preferred_city.lower():
                location_bonus = 10
            
            return min(base_score + bonus_score + location_bonus, 100)
        
        for amenity_name, is_preferred in user_amenity_prefs.items():
            if is_preferred:
                has_amenity = False
                
                if amenity_name == 'wifi' and any(name.lower().find('wi-fi') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'parking' and any(name.lower().find('parking') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'pool' and any(name.lower().find('pool') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'spa' and any(name.lower().find('spa') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'gym' and any(name.lower().find('gym') != -1 or name.lower().find('fitness') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'restaurant' and any(name.lower().find('restaurant') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'room_service' and any(name.lower().find('room service') != -1 for name in amenity_names):
                    has_amenity = True
                elif amenity_name == 'air_conditioning' and any(name.lower().find('air conditioning') != -1 or name.lower().find('a/c') != -1 for name in amenity_names):
                    has_amenity = True
                
                if has_amenity:
                    required_amenities_score += 1
        
        amenities_match_percentage = (required_amenities_score / required_amenities_count) * 100
        
        if required_amenities_score < required_amenities_count:
            missing_count = required_amenities_count - required_amenities_score
            max_score = max(100 - (missing_count * 25), 0)
        
        extra_amenities = len(amenity_names) - required_amenities_score
        if extra_amenities > 0 and required_amenities_score == required_amenities_count:
            bonus_score = min(extra_amenities, 5) * 1  
        
        location_score = 0
        if user_preferences.preferred_city and self.city.lower() == user_preferences.preferred_city.lower():
            location_score = 10  
        
        if hasattr(user_preferences, 'preferred_district') and user_preferences.preferred_district and self.district and self.district.lower() == user_preferences.preferred_district.lower():
            location_score += 5  
        
        star_rating_score = 0
        if user_preferences.min_star_rating:
            if self.star_rating >= user_preferences.min_star_rating:
                star_rating_score = 5  
            else:
                max_score = max(max_score - 20, 0)  
        
        additional_score = 0
        if hasattr(user_preferences, 'prefer_pet_friendly') and user_preferences.prefer_pet_friendly:
            if hasattr(self, 'is_pet_friendly') and self.is_pet_friendly:
                additional_score += 5
            else:
                max_score = max(max_score - 15, 0)  
        
        if hasattr(user_preferences, 'prefer_family_friendly') and user_preferences.prefer_family_friendly:
            if hasattr(self, 'is_family_friendly') and self.is_family_friendly:
                additional_score += 5
            else:
                max_score = max(max_score - 15, 0)  
        
        final_score = min(amenities_match_percentage + bonus_score + location_score + star_rating_score + additional_score, max_score)
        
        return int(final_score)

class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='hotel_images/')
    caption = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Image for {self.hotel.name}"
 
class HotelAmenity(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='amenities')
    name = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = 'Hotel Amenities'
    
    def __str__(self):
        return f"{self.name} at {self.hotel.name}"

class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveSmallIntegerField(default=2)
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} at {self.hotel.name}"

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'hotel')  
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.username} favorited {self.hotel.name}"