# hotels/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import Hotel, Room
from accounts.models import UserPreference

def hotel_list(request):
    hotels = Hotel.objects.all()
    
    # Filter by search query if provided
    search_query = request.GET.get('search', '')
    if search_query:
        hotels = hotels.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(district__icontains=search_query)
        )
    
    # Filter by star rating if provided
    star_rating = request.GET.get('star_rating')
    if star_rating and star_rating.isdigit():
        hotels = hotels.filter(star_rating=int(star_rating))
    
    # Filter by amenities if provided
    amenities = request.GET.getlist('amenities')
    if amenities:
        for amenity in amenities:
            hotels = hotels.filter(amenities__name=amenity)
    
    # Paginate results
    paginator = Paginator(hotels, 12)  # Show 12 hotels per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'star_rating': star_rating,
        'selected_amenities': amenities,
    }
    
    return render(request, 'hotels/hotel_list.html', context)

def hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    rooms = hotel.rooms.all()
    amenities = hotel.amenities.all()
    
    # Get match score if user is logged in and has preferences
    match_score = None
    if request.user.is_authenticated:
        try:
            user_preferences = request.user.preferences
            
            # Calculate match score directly (similar to the hotel_recommendations view)
            score = 0
            amenity_names = [amenity.name.lower() for amenity in amenities]
            
            if user_preferences.wifi and any('wi-fi' in name for name in amenity_names):
                score += 1
            
            if user_preferences.parking and any('parking' in name for name in amenity_names):
                score += 1
            
            if user_preferences.pool and any('pool' in name for name in amenity_names):
                score += 1
            
            if user_preferences.spa and any('spa' in name for name in amenity_names):
                score += 1
            
            if user_preferences.gym and any(('gym' in name or 'fitness' in name) for name in amenity_names):
                score += 1
            
            if user_preferences.restaurant and any('restaurant' in name for name in amenity_names):
                score += 1
            
            if user_preferences.room_service and any('room service' in name for name in amenity_names):
                score += 1
            
            if user_preferences.air_conditioning and any(('air conditioning' in name or 'a/c' in name) for name in amenity_names):
                score += 1
            
            # Calculate percentage match
            match_score = int((score / 8) * 100) if score > 0 else 0
            
        except UserPreference.DoesNotExist:
            pass
    
    context = {
        'hotel': hotel,
        'rooms': rooms,
        'amenities': amenities,
        'match_score': match_score,
    }
    
    return render(request, 'hotels/hotel_detail.html', context)

@login_required
def hotel_recommendations(request):
    """
    View function to display hotel recommendations based on user preferences.
    """
    try:
        user_preferences = request.user.preferences
    except UserPreference.DoesNotExist:
        # If user has no preferences, redirect to set preferences
        return redirect('set_preferences')
    
    # Get all hotels - don't filter too much to ensure we have results
    hotels = Hotel.objects.all()
    
    # Apply only essential filters
    if user_preferences.min_star_rating:
        hotels = hotels.filter(star_rating__gte=user_preferences.min_star_rating)
    
    # Convert to list for processing
    hotels_list = list(hotels)
    
    # Print for debugging
    print(f"Found {len(hotels_list)} hotels after filtering")
    
    # Calculate match score for each hotel
    hotel_matches = []
    for hotel in hotels_list:
        score = 0
        max_score = 0  # Track max possible score for each hotel
        
        # Get amenities
        amenities = hotel.amenities.all()
        amenity_names = [amenity.name.lower() for amenity in amenities]
        
        # Check WiFi
        if user_preferences.wifi:
            max_score += 1
            if any('wi-fi' in name for name in amenity_names):
                score += 1
        
        # Check Parking
        if user_preferences.parking:
            max_score += 1
            if any('parking' in name for name in amenity_names):
                score += 1
        
        # Check Pool
        if user_preferences.pool:
            max_score += 1
            if any('pool' in name for name in amenity_names):
                score += 1
        
        # Check Spa
        if user_preferences.spa:
            max_score += 1
            if any('spa' in name for name in amenity_names):
                score += 1
        
        # Check Gym/Fitness
        if user_preferences.gym:
            max_score += 1
            if any(('gym' in name or 'fitness' in name) for name in amenity_names):
                score += 1
        
        # Check Restaurant
        if user_preferences.restaurant:
            max_score += 1
            if any('restaurant' in name for name in amenity_names):
                score += 1
        
        # Check Room Service
        if user_preferences.room_service:
            max_score += 1
            if any('room service' in name for name in amenity_names):
                score += 1
        
        # Check Air Conditioning
        if user_preferences.air_conditioning:
            max_score += 1
            if any(('air conditioning' in name or 'a/c' in name) for name in amenity_names):
                score += 1
        
        # Check Location
        if user_preferences.preferred_city:
            max_score += 1
            if user_preferences.preferred_city.lower() in hotel.city.lower():
                score += 1
        
        # Check Pet-Friendly
        if user_preferences.prefer_pet_friendly:
            max_score += 1
            if hotel.is_pet_friendly:
                score += 1
        
        # Check Family-Friendly
        if user_preferences.prefer_family_friendly:
            max_score += 1
            if hotel.is_family_friendly:
                score += 1
        
        # Calculate percentage match (avoid division by zero)
        match_score = 0
        if max_score > 0:
            match_score = int((score / max_score) * 100)
        
        # Add to matches list
        hotel_matches.append((hotel, match_score))
        
        # Debug info
        print(f"Hotel: {hotel.name}, Score: {score}/{max_score}, Match: {match_score}%")
    
    # Sort hotels by match score (highest first)
    hotel_matches.sort(key=lambda x: x[1], reverse=True)
    
    # Paginate results
    paginator = Paginator(hotel_matches, 6)  # Show 6 hotels per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'hotels/recommendations.html', context)

def search_hotels(request):
    query = request.GET.get('q', '')
    city = request.GET.get('city', '')
    check_in = request.GET.get('check_in', '')
    check_out = request.GET.get('check_out', '')
    guests = request.GET.get('guests', 1)
    
    # Base queryset
    hotels = Hotel.objects.all()
    
    # Apply filters
    if query:
        hotels = hotels.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    if city:
        hotels = hotels.filter(city__icontains=city)
    
    # Filter for room availability (simplified)
    if check_in and check_out and guests:
        # This is a simplified version - in a real app, you'd check actual availability
        hotels = hotels.filter(rooms__capacity__gte=guests)
    
    # Convert to list for processing
    hotels_list = list(hotels)
    
    # Get match scores if user is logged in
    hotel_matches = []
    if request.user.is_authenticated:
        try:
            user_preferences = request.user.preferences
            
            for hotel in hotels_list:
                # Calculate match score directly
                score = 0
                amenities = hotel.amenities.all()
                amenity_names = [amenity.name.lower() for amenity in amenities]
                
                if user_preferences.wifi and any('wi-fi' in name for name in amenity_names):
                    score += 1
                
                if user_preferences.parking and any('parking' in name for name in amenity_names):
                    score += 1
                
                if user_preferences.pool and any('pool' in name for name in amenity_names):
                    score += 1
                
                if user_preferences.spa and any('spa' in name for name in amenity_names):
                    score += 1
                
                if user_preferences.gym and any(('gym' in name or 'fitness' in name) for name in amenity_names):
                    score += 1
                
                if user_preferences.restaurant and any('restaurant' in name for name in amenity_names):
                    score += 1
                
                if user_preferences.room_service and any('room service' in name for name in amenity_names):
                    score += 1
                
                if user_preferences.air_conditioning and any(('air conditioning' in name or 'a/c' in name) for name in amenity_names):
                    score += 1
                
                # Calculate percentage match
                match_score = int((score / 8) * 100) if score > 0 else 0
                hotel_matches.append((hotel, match_score))
            
            # Sort by match score
            hotel_matches.sort(key=lambda x: x[1], reverse=True)
        except UserPreference.DoesNotExist:
            hotel_matches = [(hotel, None) for hotel in hotels_list]
    else:
        hotel_matches = [(hotel, None) for hotel in hotels_list]
    
    # Paginate results
    paginator = Paginator(hotel_matches, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'city': city,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
    }
    
    return render(request, 'hotels/search_results.html', context)