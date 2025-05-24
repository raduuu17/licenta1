# hotels/staff_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin

from .models import Hotel, HotelAmenity, Room
from .forms import HotelForm, RoomFormSet

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

class HotelDeleteView(StaffRequiredMixin, DeleteView):
    model = Hotel
    template_name = 'hotels/staff/hotel_confirm_delete.html'
    success_url = reverse_lazy('staff_hotel_list')
    
    def delete(self, request, *args, **kwargs):
        hotel = self.get_object()
        messages.success(request, f'Hotel "{hotel.name}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)