# hotels/staff_views.py
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin

from .models import Hotel, HotelAmenity, Room
from .forms import HotelForm, RoomFormSet
from .external_api import fetch_hotels_for_city, ExternalAPIError

# Helper function to check if user is staff
def is_staff(user):
    return user.is_staff

# Staff dashboard
@login_required
@user_passes_test(is_staff)
def staff_dashboard(request):
    hotels_count = Hotel.objects.count()
    rooms_count = Room.objects.count()
    recent_hotels = Hotel.objects.order_by('-created_at')[:5]
    
    context = {
        'hotels_count': hotels_count,
        'rooms_count': rooms_count,
        'recent_hotels': recent_hotels,
    }
    
    return render(request, 'hotels/staff/dashboard.html', context)

@login_required
@user_passes_test(is_staff)
def update_coordinates(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    
    if request.method == 'POST':
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        try:
            hotel.latitude = float(latitude) if latitude else None
            hotel.longitude = float(longitude) if longitude else None
            hotel.save()
            messages.success(request, f"Coordinates for {hotel.name} updated successfully.")
            return redirect('staff_hotel_detail', pk=hotel.id)
        except ValueError:
            messages.error(request, "Invalid coordinates. Please enter valid numbers.")
    
    return render(request, 'hotels/update_coordinates.html', {'hotel': hotel})

# Hotel management views
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

class HotelListView(StaffRequiredMixin, ListView):
    model = Hotel
    template_name = 'hotels/staff/hotel_list.html'
    context_object_name = 'hotels'
    ordering = ['-created_at']
    paginate_by = 10

@login_required
@user_passes_test(is_staff)
def create_hotel(request):
    if request.method == 'POST':
        form = HotelForm(request.POST, request.FILES)
        room_formset = RoomFormSet(request.POST, request.FILES, prefix='rooms')
        
        # Debug information
        print("Form is valid:", form.is_valid())
        if not form.is_valid():
            print("Form errors:", form.errors)
        
        print("Room formset is valid:", room_formset.is_valid())
        if not room_formset.is_valid():
            print("Room formset errors:", room_formset.errors)
            print("Room formset non-form errors:", room_formset.non_form_errors())
        
        if form.is_valid() and room_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save the hotel and amenities
                    hotel = form.save()
                    print("Hotel saved successfully:", hotel.id)
                    
                    # Save rooms
                    room_formset.instance = hotel
                    room_formset.save()
                    print("Rooms saved successfully")
                    
                messages.success(request, f'Hotel "{hotel.name}" has been created successfully!')
                return redirect('staff_hotel_list')
            except Exception as e:
                print("Exception during save:", str(e))
                messages.error(request, f"Error saving hotel: {str(e)}")
        else:
            # Add form errors to messages for visibility
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            
            if not room_formset.is_valid():
                messages.error(request, "There are errors in the room information.")
    else:
        form = HotelForm()
        room_formset = RoomFormSet(prefix='rooms')
    
    context = {
        'form': form,
        'room_formset': room_formset,
        'title': 'Add New Hotel',
    }
    
    return render(request, 'hotels/staff/hotel_form.html', context)

@login_required
@user_passes_test(is_staff)
def update_hotel(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    
    if request.method == 'POST':
        form = HotelForm(request.POST, request.FILES, instance=hotel)
        room_formset = RoomFormSet(request.POST, request.FILES, instance=hotel, prefix='rooms')
        
        # Debug information
        print("Form is valid:", form.is_valid())
        if not form.is_valid():
            print("Form errors:", form.errors)
        
        print("Room formset is valid:", room_formset.is_valid())
        if not room_formset.is_valid():
            print("Room formset errors:", room_formset.errors)
            print("Room formset non-form errors:", room_formset.non_form_errors())
        
        if form.is_valid() and room_formset.is_valid():
            try:
                with transaction.atomic():
                    # Save the hotel and amenities
                    hotel = form.save()
                    print("Hotel updated successfully:", hotel.id)
                    
                    # Save rooms
                    room_formset.save()
                    print("Rooms saved successfully")
                    
                messages.success(request, f'Hotel "{hotel.name}" has been updated successfully!')
                return redirect('staff_hotel_detail', pk=hotel.pk)
            except Exception as e:
                print("Exception during save:", str(e))
                messages.error(request, f"Error updating hotel: {str(e)}")
        else:
            # Add form errors to messages for visibility
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            
            if not room_formset.is_valid():
                messages.error(request, "There are errors in the room information.")
    else:
        form = HotelForm(instance=hotel)
        room_formset = RoomFormSet(instance=hotel, prefix='rooms')
    
    context = {
        'form': form,
        'room_formset': room_formset,
        'hotel': hotel,
        'title': f'Edit Hotel: {hotel.name}',
    }
    
    return render(request, 'hotels/staff/hotel_form.html', context)

@login_required
@user_passes_test(is_staff)
def hotel_detail(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    amenities = hotel.amenities.all()
    rooms = hotel.rooms.all()
    
    context = {
        'hotel': hotel,
        'amenities': amenities,
        'rooms': rooms,
    }
    
    return render(request, 'hotels/staff/hotel_detail.html', context)

DEFAULT_ROOM_TYPES = [
    ('Standard Room', 2, 1.0),
    ('Double Room', 3, 1.4),
    ('Suite', 4, 2.0),
]

DEFAULT_AMENITY_POOL = [
    ('Free Wi-Fi', 1, 1.0),
    ('Parking', 2, 0.7),
    ('Air Conditioning', 3, 0.9),
    ('Restaurant', 3, 0.8),
    ('Room Service', 3, 0.6),
    ('Bar', 3, 0.5),
    ('Fitness Center (Gym)', 4, 0.8),
    ('Spa & Wellness', 4, 0.5),
    ('Swimming Pool', 4, 0.4),
    ('Sauna', 4, 0.3),
]

def apply_imported_hotel_details(hotel, data):
    rng = random.Random(hotel.name.lower())

    amenity_names = set(data.get('amenities', []))
    for name, min_stars, probability in DEFAULT_AMENITY_POOL:
        if hotel.star_rating >= min_stars and rng.random() < probability:
            amenity_names.add(name)
    if hotel.star_rating == 5:
        amenity_names.update({'Swimming Pool', 'Spa & Wellness', 'Fitness Center (Gym)', 'Room Service'})

    hotel.amenities.all().delete()
    for name in sorted(amenity_names):
        HotelAmenity.objects.create(hotel=hotel, name=name)

    hotel.is_pet_friendly = data.get('is_pet_friendly', False) or rng.random() < 0.3
    hotel.is_family_friendly = hotel.star_rating >= 3 or rng.random() < 0.5
    if data.get('district'):
        hotel.district = data['district']

    location = hotel.city
    if hotel.district:
        location += f" ({hotel.district})"
    parts = [
        f"{hotel.name} is a {hotel.star_rating}-star hotel located in {location}.",
        f"Amenities include: {', '.join(sorted(amenity_names))}.",
    ]
    if hotel.is_pet_friendly:
        parts.append("Pets are welcome.")
    if hotel.is_family_friendly:
        parts.append("Great for families.")
    if data.get('website'):
        parts.append(f"Website: {data['website']}")
    if data.get('phone'):
        parts.append(f"Phone: {data['phone']}")
    parts.append("Imported automatically from OpenStreetMap.")
    hotel.description = ' '.join(parts)

    hotel.save()

def _create_default_rooms(hotel):
    base_price = 40 + hotel.star_rating * 25
    for name, capacity, multiplier in DEFAULT_ROOM_TYPES:
        Room.objects.create(
            hotel=hotel,
            name=name,
            description=f"{name} at {hotel.name}, comfortable accommodation for up to {capacity} guests.",
            price=round(base_price * multiplier, 2),
            capacity=capacity,
        )

IMPORT_BATCH_SIZE = 20
FETCH_POOL_SIZE = 200

@login_required
@user_passes_test(is_staff)
def import_hotels(request):
    results = None
    city = ''

    if request.method == 'POST':
        city = request.POST.get('city', '').strip()
        create_rooms = request.POST.get('create_rooms') == 'on'

        if not city:
            messages.error(request, "Please enter a city name.")
        else:
            try:
                fetched = fetch_hotels_for_city(city, limit=FETCH_POOL_SIZE)
            except ExternalAPIError as e:
                messages.error(request, str(e))
                fetched = None

            if fetched is not None:
                if not fetched:
                    messages.warning(request, f'No hotels were found for "{city}".')

                results = {'imported': [], 'skipped': []}
                for data in fetched:
                    # Stop once this run imported a full batch of new hotels
                    if len(results['imported']) >= IMPORT_BATCH_SIZE:
                        break

                    # Duplicate check: same name in the same city
                    if Hotel.objects.filter(name__iexact=data['name'], city__iexact=data['city']).exists():
                        results['skipped'].append(data)
                        continue

                    with transaction.atomic():
                        hotel = Hotel.objects.create(
                            name=data['name'],
                            description='',
                            address=data['address'],
                            city=data['city'],
                            star_rating=data['star_rating'],
                            latitude=data['latitude'],
                            longitude=data['longitude'],
                        )
                        apply_imported_hotel_details(hotel, data)
                        if create_rooms:
                            _create_default_rooms(hotel)
                    results['imported'].append(data)

                if results['imported']:
                    messages.success(
                        request,
                        f"{len(results['imported'])} hotels imported for \"{city}\" "
                        f"({len(results['skipped'])} skipped as duplicates)."
                    )
                elif results['skipped']:
                    messages.info(request, f"All {len(results['skipped'])} hotels found already exist - nothing to import.")

    context = {
        'results': results,
        'city': city,
    }
    return render(request, 'hotels/staff/hotel_import.html', context)

class HotelDeleteView(StaffRequiredMixin, DeleteView):
    model = Hotel
    template_name = 'hotels/staff/hotel_confirm_delete.html'
    success_url = reverse_lazy('staff_hotel_list')
    
    def delete(self, request, *args, **kwargs):
        hotel = self.get_object()
        messages.success(request, f'Hotel "{hotel.name}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)