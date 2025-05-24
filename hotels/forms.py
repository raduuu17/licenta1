# hotels/forms.py
from django import forms
from .models import Hotel, HotelAmenity, Room

class HotelForm(forms.ModelForm):
    STAR_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    star_rating = forms.ChoiceField(choices=STAR_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    
    # Common amenities as checkboxes
    wifi = forms.BooleanField(required=False, label='Wi-Fi', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    parking = forms.BooleanField(required=False, label='Free Parking', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    pool = forms.BooleanField(required=False, label='Swimming Pool', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    spa = forms.BooleanField(required=False, label='Spa & Wellness', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    gym = forms.BooleanField(required=False, label='Fitness Center', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    restaurant = forms.BooleanField(required=False, label='On-site Restaurant', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    room_service = forms.BooleanField(required=False, label='Room Service', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    air_conditioning = forms.BooleanField(required=False, label='Air Conditioning', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    bar = forms.BooleanField(required=False, label='Bar/Lounge', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    breakfast = forms.BooleanField(required=False, label='Breakfast Included', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    class Meta:
        model = Hotel
        fields = ['name', 'description', 'address', 'city', 'district', 
                  'star_rating', 'image', 'is_pet_friendly', 'is_family_friendly']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'is_pet_friendly': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_family_friendly': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        hotel = super().save(commit=commit)
        
        if commit:
            # Clear existing amenities
            hotel.amenities.all().delete()
            
            # Create amenities based on checkbox selections
            amenities = []
            if self.cleaned_data.get('wifi'):
                amenities.append(HotelAmenity(hotel=hotel, name='Wi-Fi'))
            if self.cleaned_data.get('parking'):
                amenities.append(HotelAmenity(hotel=hotel, name='Free Parking'))
            if self.cleaned_data.get('pool'):
                amenities.append(HotelAmenity(hotel=hotel, name='Swimming Pool'))
            if self.cleaned_data.get('spa'):
                amenities.append(HotelAmenity(hotel=hotel, name='Spa & Wellness'))
            if self.cleaned_data.get('gym'):
                amenities.append(HotelAmenity(hotel=hotel, name='Fitness Center'))
            if self.cleaned_data.get('restaurant'):
                amenities.append(HotelAmenity(hotel=hotel, name='On-site Restaurant'))
            if self.cleaned_data.get('room_service'):
                amenities.append(HotelAmenity(hotel=hotel, name='Room Service'))
            if self.cleaned_data.get('air_conditioning'):
                amenities.append(HotelAmenity(hotel=hotel, name='Air Conditioning'))
            if self.cleaned_data.get('bar'):
                amenities.append(HotelAmenity(hotel=hotel, name='Bar/Lounge'))
            if self.cleaned_data.get('breakfast'):
                amenities.append(HotelAmenity(hotel=hotel, name='Breakfast Included'))
            
            # Bulk create amenities
            if amenities:
                HotelAmenity.objects.bulk_create(amenities)
        
        return hotel
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        
        # If editing an existing hotel, check amenities that exist
        if instance:
            amenity_names = [amenity.name for amenity in instance.amenities.all()]
            self.fields['wifi'].initial = 'Wi-Fi' in amenity_names
            self.fields['parking'].initial = 'Free Parking' in amenity_names
            self.fields['pool'].initial = 'Swimming Pool' in amenity_names
            self.fields['spa'].initial = 'Spa & Wellness' in amenity_names
            self.fields['gym'].initial = 'Fitness Center' in amenity_names
            self.fields['restaurant'].initial = 'On-site Restaurant' in amenity_names
            self.fields['room_service'].initial = 'Room Service' in amenity_names
            self.fields['air_conditioning'].initial = 'Air Conditioning' in amenity_names
            self.fields['bar'].initial = 'Bar/Lounge' in amenity_names
            self.fields['breakfast'].initial = 'Breakfast Included' in amenity_names

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['name', 'description', 'price', 'capacity', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'min': 0, 'step': 0.01}),
            'capacity': forms.NumberInput(attrs={'min': 1}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

RoomFormSet = forms.inlineformset_factory(
    Hotel, Room, form=RoomForm, 
    extra=1, can_delete=True, 
    min_num=1, validate_min=True
)