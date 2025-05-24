from django.db import models

class Hotel(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)
    star_rating = models.PositiveSmallIntegerField(default=3)
    image = models.ImageField(upload_to='hotel_images/', blank=True, null=True)  # Keep for backward compatibility
    is_pet_friendly = models.BooleanField(default=False)
    is_family_friendly = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_amenities(self):
        return self.amenities.all()
    
    def main_image(self):
        # Return the main image or the first image from the gallery if available
        if self.image:
            return self.image.url
        
        first_image = self.images.first()
        if first_image:
            return first_image.image.url
        
        return None

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
    
def match_score(self, user_preferences):
    """Calculate how well this hotel matches a user's preferences"""
    score = 0
    max_possible_score = 0
    
    # Check amenities
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
    
    amenities = self.amenities.all()
    amenity_names = [amenity.name.lower() for amenity in amenities]
    
    for amenity_name, is_preferred in user_amenity_prefs.items():
        if is_preferred:
            max_possible_score += 1
            # Check if hotel has this amenity (allowing for some variation in naming)
            if amenity_name == 'wifi' and any(name.lower().find('wi-fi') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'parking' and any(name.lower().find('parking') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'pool' and any(name.lower().find('pool') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'spa' and any(name.lower().find('spa') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'gym' and any(name.lower().find('gym') != -1 or name.lower().find('fitness') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'restaurant' and any(name.lower().find('restaurant') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'room_service' and any(name.lower().find('room service') != -1 for name in amenity_names):
                score += 1
            elif amenity_name == 'air_conditioning' and any(name.lower().find('air conditioning') != -1 or name.lower().find('a/c') != -1 for name in amenity_names):
                score += 1
    
    # Check location preferences
    if user_preferences.preferred_city and self.city.lower() == user_preferences.preferred_city.lower():
        score += 2
        max_possible_score += 2
    
    if user_preferences.preferred_district and self.district.lower() == user_preferences.preferred_district.lower():
        score += 1
        max_possible_score += 1
    
    # Check star rating
    if user_preferences.min_star_rating:
        max_possible_score += 1
        if self.star_rating >= user_preferences.min_star_rating:
            score += 1
    
    # Check pet-friendly status
    if user_preferences.prefer_pet_friendly:
        max_possible_score += 1
        if self.is_pet_friendly:
            score += 1
    
    # Check family-friendly status
    if user_preferences.prefer_family_friendly:
        max_possible_score += 1
        if self.is_family_friendly:
            score += 1
    
    # Calculate percentage match
    percentage = (score / max_possible_score * 100) if max_possible_score > 0 else 0
    return int(percentage)

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