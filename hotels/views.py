# hotels/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.db import models
from datetime import datetime
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg

from .models import Hotel, Room, Favorite
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
    star_rating = request.GET.get('star_rating', '')
    if star_rating and star_rating.isdigit():
        hotels = hotels.filter(star_rating=int(star_rating))
    
    hotels = Hotel.objects.all()
    # Filter by amenities if provided
    selected_amenities = request.GET.getlist('amenities[]', [])
    amenity_mapping = {
        'wifi': ['wifi', 'wi-fi', 'wi fi', 'internet'],
        'air_conditioning': ['air conditioning', 'ac', 'a/c', 'air con'],
        'room_service': ['room service'],
        'gym': ['gym', 'fitness', 'fitness center', 'fitness centre'],
        'parking': ['parking', 'free parking', 'valet parking'],
        'pool': ['pool', 'swimming pool', 'indoor pool', 'outdoor pool'],
        'spa': ['spa', 'wellness', 'massage'],
        'restaurant': ['restaurant', 'dining', 'on-site restaurant']
    }
    
    # Apply amenity filters
    for amenity in selected_amenities:
        if amenity in amenity_mapping:
            # Create a Q object for OR conditions
            q_objects = Q()
            for term in amenity_mapping[amenity]:
                q_objects |= Q(amenities__name__icontains=term)
            hotels = hotels.filter(q_objects)
        else:
            # Fallback for any amenity not in the mapping
            hotels = hotels.filter(amenities__name__icontains=amenity)
    
    # Make sure we don't have duplicates after all the OR conditions
    hotels = hotels.distinct()

    # Paginate results
    paginator = Paginator(hotels, 12)  # Show 12 hotels per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'star_rating': star_rating,
        'selected_amenities': selected_amenities,
    }
    
    return render(request, 'hotels/hotel_list.html', context)

def hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    rooms = hotel.rooms.all()
    amenities = hotel.amenities.all()

    avg_rating_result = hotel.reviews.aggregate(avg=Avg('rating'))
    avg_rating = avg_rating_result['avg'] if avg_rating_result['avg'] is not None else 0
    
    match_score = None
    if request.user.is_authenticated:
        try:
            user_preferences = request.user.preferences
            
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
            match_score = int((score / 8) * 100) if score > 0 else 0
            
        except UserPreference.DoesNotExist:
            pass
    
    context = {
        'hotel': hotel,
        'rooms': rooms,
        'amenities': amenities,
        'match_score': match_score,
        'avg_rating': avg_rating
    }
    
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, hotel=hotel).exists()
        context['is_favorite'] = is_favorite
    
    return render(request, 'hotels/hotel_detail.html', context)

@login_required
def hotel_recommendations(request):
    try:
        user_preferences = request.user.preferences
    except UserPreference.DoesNotExist:
        return redirect('set_preferences')
    
    hotels = Hotel.objects.all()
    
    if user_preferences.min_star_rating:
        hotels = hotels.filter(star_rating__gte=user_preferences.min_star_rating)
    
    hotels_list = list(hotels)
    
    print(f"Found {len(hotels_list)} hotels after filtering")
    
    hotel_matches = []
    for hotel in hotels_list:
        match_score = hotel.match_score(user_preferences)
        hotel_matches.append((hotel, match_score))
        
        print(f"Hotel: {hotel.name}, Match: {match_score}%")
    
    hotel_matches.sort(key=lambda x: x[1], reverse=True)
    
    paginator = Paginator(hotel_matches, 6) 
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

    today = datetime.now().date()
    error_message = None
    
    if check_in:
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            if check_in_date < today:
                error_message = "Check-in date cannot be in the past."
                check_in = today.strftime('%Y-%m-%d') 
        except ValueError:
            error_message = "Invalid check-in date format."
            check_in = ''
    
    if check_out:
        try:
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            if check_out_date < today:
                error_message = "Check-out date cannot be in the past."
                check_out = ''
            elif check_in and check_out_date < datetime.strptime(check_in, '%Y-%m-%d').date():
                error_message = "Check-out date must be after check-in date."
                check_out = ''
        except ValueError:
            error_message = "Invalid check-out date format."
            check_out = ''
    
    hotels = Hotel.objects.all()
    
    if query:
        hotels = hotels.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    if city:
        hotels = hotels.filter(city__icontains=city)
    
    if check_in and check_out and guests:
        hotels = hotels.filter(rooms__capacity__gte=guests)
        hotels = hotels.distinct()
    
    hotels_list = list(hotels)
    
    hotel_matches = []
    if request.user.is_authenticated:
        try:
            user_preferences = request.user.preferences
            
            hotel_matches = [(hotel, hotel.match_score(user_preferences)) for hotel in hotels_list]
            
            hotel_matches.sort(key=lambda x: x[1], reverse=True)
        except UserPreference.DoesNotExist:
            hotel_matches = [(hotel, None) for hotel in hotels_list]
    else:
        hotel_matches = [(hotel, None) for hotel in hotels_list]
    
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

@login_required
def toggle_favorite(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, hotel=hotel)
    
    if not created:
        favorite.delete()
        is_favorite = False
        messages.success(request, f"{hotel.name} removed from favorites")
    else:
        is_favorite = True
        messages.success(request, f"{hotel.name} added to favorites")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'is_favorite': is_favorite,
            'hotel_id': hotel_id
        })
    
    return redirect(request.META.get('HTTP_REFERER', 'hotel_list'))

@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('hotel')
    
    hotel_matches = []
    try:
        user_preferences = request.user.preferences
        for favorite in favorites:
            hotel = favorite.hotel
            match_score = hotel.match_score(user_preferences)
            hotel_matches.append((hotel, match_score))
    except UserPreference.DoesNotExist:
        hotel_matches = [(favorite.hotel, None) for favorite in favorites]
    
    paginator = Paginator(hotel_matches, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'hotels/favorites.html', {'page_obj': page_obj})