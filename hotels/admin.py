from django.contrib import admin
from .models import Hotel, HotelAmenity, Room, HotelImage

class HotelAmenityInline(admin.TabularInline):
    model = HotelAmenity
    extra = 1

class RoomInline(admin.TabularInline):
    model = Room
    extra = 1

class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'star_rating', 'is_pet_friendly', 'is_family_friendly', 'created_at')
    list_filter = ('star_rating', 'city', 'is_pet_friendly', 'is_family_friendly')
    search_fields = ('name', 'description', 'city', 'district')
    inlines = [HotelAmenityInline, RoomInline, HotelImageInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'image')
        }),
        ('Location', {
            'fields': ('address', 'city', 'district')
        }),
        ('Features', {
            'fields': ('star_rating', 'is_pet_friendly', 'is_family_friendly')
        }),
    )

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'hotel', 'price', 'capacity', 'is_available')
    list_filter = ('is_available', 'capacity', 'hotel')
    search_fields = ('name', 'description', 'hotel__name')

@admin.register(HotelImage)
class HotelImageAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'caption', 'is_main', 'order')
    list_filter = ('hotel', 'is_main')
    search_fields = ('hotel__name', 'caption')