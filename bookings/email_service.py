import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def send_booking_confirmation_email(booking, request=None):
    """Send an email with the booking details to the user who made the booking."""
    user = booking.user
    if not user.email:
        logger.warning(f"User {user.username} has no email address; skipping booking confirmation email.")
        return False

    nights = (booking.check_out_date - booking.check_in_date).days
    booking_url = ''
    if request is not None:
        booking_url = request.build_absolute_uri(
            reverse('booking_detail', kwargs={'booking_id': booking.id})
        )

    context = {
        'booking': booking,
        'user': user,
        'hotel': booking.room.hotel,
        'room': booking.room,
        'nights': nights,
        'booking_url': booking_url,
    }

    subject = f"Booking confirmation #{booking.id} - {booking.room.hotel.name}"
    text_body = render_to_string('booking/email/booking_confirmation.txt', context)
    html_body = render_to_string('booking/email/booking_confirmation.html', context)

    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_body, 'text/html')
        email.send()
        return True
    except Exception:
        logger.exception(f"Failed to send booking confirmation email for booking #{booking.id}")
        return False
