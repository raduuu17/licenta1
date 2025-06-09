from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from hotels.models import Hotel, Room
from django.db.models.signals import post_save
from django.dispatch import receiver

class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CHECKED_IN = 'checked_in', 'Checked In'
    CHECKED_OUT = 'checked_out', 'Checked Out'
    CANCELLED = 'cancelled', 'Cancelled'

class PaymentStatus(models.TextChoices):
    NOT_PAID = 'not_paid', 'Not Paid'
    PARTIALLY_PAID = 'partially_paid', 'Partially Paid'
    PAID = 'paid', 'Paid'
    REFUNDED = 'refunded', 'Refunded'

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='bookings')
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    guests = models.PositiveSmallIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    special_requests = models.TextField(blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_PAID
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Booking #{self.id} - {self.user.username} at {self.room.hotel.name}"
    
    def clean(self):
        # First check if room is assigned, otherwise don't try to validate room-related constraints
        if not hasattr(self, 'room') or self.room is None:
            # Skip room-related validations if room is not yet assigned
            return
        
        # Check that check-out is after check-in
        if self.check_out_date <= self.check_in_date:
            raise ValidationError("Check-out date must be after check-in date")
        
        # Check that check-in is not in the past
        if self.check_in_date < timezone.now().date():
            raise ValidationError("Check-in date cannot be in the past")
        
        # Check for room capacity - only if room is already set
        if self.guests > self.room.capacity:
            raise ValidationError(f"This room can only accommodate {self.room.capacity} guests")
        
        # Check room availability - only if room is already set
        overlapping_bookings = Booking.objects.filter(
            room=self.room,
            check_in_date__lt=self.check_out_date,
            check_out_date__gt=self.check_in_date
        ).exclude(pk=self.pk).exclude(status=BookingStatus.CANCELLED)
        
        if overlapping_bookings.exists():
            raise ValidationError("This room is not available for the selected dates")

    def save(self, *args, **kwargs):
        # Calculate total price if not set
        if not self.total_price and hasattr(self, 'room') and self.room is not None:
            # Only calculate price if room is set
            nights = (self.check_out_date - self.check_in_date).days
            self.total_price = self.room.price * nights
        
        # Only call full_clean if we're not in the middle of setting up the object
        if hasattr(self, 'room') and self.room is not None:
            self.full_clean()
        
        super().save(*args, **kwargs)
    
    def cancel(self):
        """Cancel this booking"""
        self.status = BookingStatus.CANCELLED
        self.save()
        
        # Trigger cancellation notification
        self.send_cancellation_notification()
        return True
    
    def confirm(self):
        """Confirm this booking"""
        self.status = BookingStatus.CONFIRMED
        self.save()
        
        # Trigger confirmation notification
        self.send_confirmation_notification()
        return True
    
    def check_in(self):
        """Mark this booking as checked in"""
        if self.status != BookingStatus.CONFIRMED:
            raise ValidationError("Only confirmed bookings can be checked in")
        
        self.status = BookingStatus.CHECKED_IN
        self.save()
        return True
    
    def check_out(self):
        """Mark this booking as checked out"""
        if self.status != BookingStatus.CHECKED_IN:
            raise ValidationError("Only checked-in bookings can be checked out")
        
        self.status = BookingStatus.CHECKED_OUT
        self.save()
        return True
    
    def get_cancellation_policy(self):
        """Get cancellation policy for this booking"""
        # Calculate days until check-in
        days_until_checkin = (self.check_in_date - timezone.now().date()).days
        
        if days_until_checkin >= 7:
            return "Full refund"
        elif days_until_checkin >= 3:
            return "50% refund"
        else:
            return "No refund"
    
    def send_confirmation_notification(self):
        """Send booking confirmation notification to the user"""
        # This would typically integrate with your email backend
        # For now, we'll just create a notification record
        Notification.objects.create(
            user=self.user,
            booking=self,
            type=NotificationType.BOOKING_CONFIRMED,
            message=f"Your booking at {self.room.hotel.name} has been confirmed."
        )
    
    def send_cancellation_notification(self):
        """Send booking cancellation notification to the user"""
        Notification.objects.create(
            user=self.user,
            booking=self,
            type=NotificationType.BOOKING_CANCELLED,
            message=f"Your booking at {self.room.hotel.name} has been cancelled."
        )

    def update_status_after_payment(self):
        """Update booking status after payment"""
        # If booking is pending and payment is complete, confirm it
        if self.status == 'pending' and self.payment_status == 'paid':
            self.status = 'confirmed'
            self.save()
            return True
        return False

    def update_status_based_on_dates(self):
        """Update booking status based on current date in relation to check-in and check-out dates"""
        today = timezone.now().date()
        
        # Skip if booking is cancelled
        if self.status == BookingStatus.CANCELLED:
            return False
            
        # If we're between check-in and check-out dates, mark as checked in
        if self.status == BookingStatus.CONFIRMED and self.check_in_date <= today < self.check_out_date:
            self.status = BookingStatus.CHECKED_IN
            # Use update to avoid triggering full_clean() which would validate check-in date
            Booking.objects.filter(pk=self.pk).update(status=BookingStatus.CHECKED_IN)
            return True
            
        # If we're past check-out date, mark as checked out
        if (self.status == BookingStatus.CONFIRMED or self.status == BookingStatus.CHECKED_IN) and today >= self.check_out_date:
            self.status = BookingStatus.CHECKED_OUT
            # Use update to avoid triggering full_clean() which would validate check-in date
            Booking.objects.filter(pk=self.pk).update(status=BookingStatus.CHECKED_OUT)
            return True
            
        return False

class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    is_refund = models.BooleanField(default=False)
    
    def __str__(self):
        transaction_type = "Refund" if self.is_refund else "Payment"
        return f"{transaction_type} of {self.amount} for Booking #{self.booking.id}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update booking payment status
        self.update_booking_payment_status()
    
    def update_booking_payment_status(self):
        """Update the payment status of the associated booking"""
        booking = self.booking
        total_paid = booking.payments.filter(is_refund=False).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        total_refunded = booking.payments.filter(is_refund=True).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        net_paid = total_paid - total_refunded
        
        if net_paid <= 0:
            booking.payment_status = PaymentStatus.NOT_PAID
        elif net_paid < booking.total_price:
            booking.payment_status = PaymentStatus.PARTIALLY_PAID
        elif net_paid >= booking.total_price:
            booking.payment_status = PaymentStatus.PAID
        
        if total_refunded > 0 and booking.status == BookingStatus.CANCELLED:
            booking.payment_status = PaymentStatus.REFUNDED
        
        booking.save(update_fields=['payment_status'])

class NotificationType(models.TextChoices):
    BOOKING_CONFIRMED = 'booking_confirmed', 'Booking Confirmed'
    BOOKING_CANCELLED = 'booking_cancelled', 'Booking Cancelled'
    PAYMENT_RECEIVED = 'payment_received', 'Payment Received'
    REMINDER = 'reminder', 'Reminder'
    CUSTOM = 'custom', 'Custom'

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    type = models.CharField(max_length=20, choices=NotificationType.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} notification for {self.user.username}"

class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    hotel = models.ForeignKey('hotels.Hotel', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.hotel.name}"
    
    def clean(self):
        # Ensure rating is between 1 and 5
        if self.rating < 1 or self.rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        
        # Ensure the booking is completed
        if self.booking.status != BookingStatus.CHECKED_OUT:
            raise ValidationError("You can only review after checking out")
        
        # Ensure the review is for the same hotel as the booking
        if self.booking.room.hotel != self.hotel:
            raise ValidationError("Review must be for the hotel you stayed at")

@receiver(post_save, sender=Payment)
def update_booking_status_on_payment(sender, instance, created, **kwargs):
    """Update booking status when a payment is created or updated"""
    if created or instance.pk:  # If payment was created or updated
        booking = instance.booking
        booking.update_status_after_payment()