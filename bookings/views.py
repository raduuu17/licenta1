from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import Booking
from hotels.models import Room, Hotel
from .forms import BookingForm


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    return render(request, 'bookings/booking_detail.html', {'booking': booking})

@login_required
def booking_list(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    return render(request, 'bookings/booking_list.html', {'bookings': bookings})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status in ['pending', 'confirmed']:
        if request.method == 'POST':
            booking.status = 'cancelled'
            booking.save()
            messages.success(request, "Booking cancelled successfully.")
            return redirect('booking_list')
        
        return render(request, 'bookings/cancel_booking.html', {'booking': booking})
    else:
        messages.error(request, "This booking cannot be cancelled.")
        return redirect('booking_detail', booking_id=booking.id)

def send_booking_confirmation(booking):
    """Send booking confirmation email"""
    subject = f"Booking Confirmation - {booking.room.hotel.name}"
    
    context = {
        'booking': booking,
        'user': booking.user,
        'hotel': booking.room.hotel,
        'room': booking.room,
        'days': (booking.check_out_date - booking.check_in_date).days,
    }
    
    html_message = render_to_string('bookings/emails/booking_confirmation.html', context)
    plain_message = f"""
    Booking Confirmation
    
    Thank you for booking with Pausa Booking!
    
    Hotel: {booking.room.hotel.name}
    Room: {booking.room.name}
    Check-in: {booking.check_in_date}
    Check-out: {booking.check_out_date}
    Guests: {booking.guests}
    Total: ${booking.total_price}
    
    Your booking is currently {booking.get_status_display()}.
    
    Thank you,
    The Pausa Booking Team
    """
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_booking_cancellation(booking):
    """Send booking cancellation email"""
    subject = f"Booking Cancellation - {booking.room.hotel.name}"
    
    context = {
        'booking': booking,
        'user': booking.user,
        'hotel': booking.room.hotel,
    }
    
    html_message = render_to_string('bookings/emails/booking_cancellation.html', context)
    plain_message = f"""
    Booking Cancellation
    
    Your booking at {booking.room.hotel.name} has been cancelled.
    
    Booking Details:
    Room: {booking.room.name}
    Check-in: {booking.check_in_date}
    Check-out: {booking.check_out_date}
    
    If you did not request this cancellation, please contact us immediately.
    
    Thank you,
    The Pausa Booking Team
    """
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        html_message=html_message,
        fail_silently=False,
    )