from django.contrib import admin
from .models import Booking, Payment, Notification, Review

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('payment_date', 'transaction_id')

class NotificationInline(admin.TabularInline):
    model = Notification
    extra = 0
    readonly_fields = ('created_at', 'is_read')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'room_hotel', 'check_in_date', 'check_out_date', 'status', 'payment_status', 'total_price')
    list_filter = ('status', 'payment_status', 'check_in_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'room__hotel__name', 'special_requests')
    readonly_fields = ('created_at', 'updated_at')  # Changed from 'booking_date' to 'created_at'
    inlines = [PaymentInline, NotificationInline]
    
    def room_hotel(self, obj):
        return f"{obj.room.name} at {obj.room.hotel.name}"
    room_hotel.short_description = "Room & Hotel"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'amount', 'payment_date', 'transaction_id', 'is_refund')
    list_filter = ('is_refund', 'payment_date')
    search_fields = ('booking__user__username', 'transaction_id')
    readonly_fields = ('payment_date',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'hotel', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'hotel__name', 'comment')
    readonly_fields = ('created_at',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)