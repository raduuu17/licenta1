from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'hotel_name', 'check_in_date', 'check_out_date', 'status', 'total_price')
    list_filter = ('status', 'check_in_date', 'check_out_date')
    search_fields = ('user__username', 'room__name', 'room__hotel__name')
    readonly_fields = ('booking_date',)
    date_hierarchy = 'check_in_date'
    
    def hotel_name(self, obj):
        return obj.room.hotel.name
    hotel_name.short_description = 'Hotel'
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('user', 'room', 'check_in_date', 'check_out_date', 'guests', 'total_price')
        }),
        ('Status', {
            'fields': ('status', 'booking_date')
        }),
    )