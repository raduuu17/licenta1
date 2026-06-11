from django.http import JsonResponse
from django.db.models import Q
from .models import Hotel

def hotel_map_data(request):
    """
    API endpoint to get hotel map data
    """
    hotels = Hotel.objects.all()
    
    # Apply same filters as in the hotel_list view
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
    
    # Create map data
    data = []
    for hotel in hotels:
        if hotel.latitude and hotel.longitude:
            data.append({
                'id': hotel.id,
                'name': hotel.name,
                'latitude': hotel.latitude,
                'longitude': hotel.longitude,
                'address': hotel.address,
                'city': hotel.city,
                'district': hotel.district,
                'star_rating': hotel.star_rating,
                'url': f'/hotels/{hotel.id}/',
                'image_url': hotel.main_image() if hotel.main_image() else '',
            })
    
    return JsonResponse(data, safe=False)
