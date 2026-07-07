from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings
from datetime import datetime
from .models import Booking, BookingStatus, Payment, Review, Notification, NotificationType, PaymentStatus
from .forms import BookingForm, ReviewForm
from .stripe_service import StripeService
from .email_service import send_booking_confirmation_email
from hotels.models import Hotel, Room
from django.db import models
import json

@login_required
def booking_list(request):
    """View all bookings for the current user"""
    # Get all bookings
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    
    # Update booking status based on current date
    for booking in bookings:
        booking.update_status_based_on_dates()
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        bookings = bookings.filter(status=status)
    
    context = {
        'bookings': bookings,
        'statuses': BookingStatus.choices,
        'current_status': status,
    }
    return render(request, 'booking/booking_list.html', context)

@login_required
def booking_detail(request, booking_id):
    """View details of a specific booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Update status based on current date
    booking.update_status_based_on_dates()
    
    # Check if a review exists
    review = Review.objects.filter(booking=booking).first()
    can_review = booking.status == BookingStatus.CHECKED_OUT and not review
    
    booking.update_status_after_payment()

    context = {
        'booking': booking,
        'review': review,
        'can_review': can_review,
        'cancellation_policy': booking.get_cancellation_policy(),
    }
    return render(request, 'booking/booking_detail.html', context)

@login_required
def create_booking(request, room_id):
    """Create a new booking"""
    room = get_object_or_404(Room, id=room_id)
    hotel = room.hotel
    
    if request.method == 'POST':
        data = request.POST.copy()

        # The hotel page submits check_in/check_out; the form expects *_date names
        if 'check_in' in data and 'check_in_date' not in data:
            data['check_in_date'] = data['check_in']

        if 'check_out' in data and 'check_out_date' not in data:
            data['check_out_date'] = data['check_out']
        form = BookingForm(data)
        if form.is_valid():
            try:
                booking = Booking()
                booking.user = request.user
                booking.room = room 
                
                booking.check_in_date = form.cleaned_data['check_in_date']
                booking.check_out_date = form.cleaned_data['check_out_date']
                booking.guests = form.cleaned_data['guests']
                booking.special_requests = form.cleaned_data.get('special_requests', '')
                
                nights = (booking.check_out_date - booking.check_in_date).days
                booking.total_price = room.price * nights
                
                booking.save()

                # Send confirmation email with the booking details
                email_sent = send_booking_confirmation_email(booking, request)

                if email_sent:
                    messages.success(request, f"Booking created! A confirmation email was sent to {request.user.email}.")
                else:
                    messages.success(request, "Your booking has been created successfully!")
                return redirect('booking_detail', booking_id=booking.id)
            
            except ValidationError as e:
                if hasattr(e, 'message_dict'):
                    for field, errors in e.message_dict.items():
                        for error in errors:
                            form.add_error(field if field else None, error)
                else:
                    form.add_error(None, str(e))
            except Exception as e:
                form.add_error(None, f"An unexpected error occurred: {str(e)}")
    else:
        # Pre-fill the form with dates/guests carried over from the hotel page
        def parse_date(value):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                return None

        initial_data = {}
        check_in = parse_date(request.GET.get('check_in'))
        check_out = parse_date(request.GET.get('check_out'))
        guests = request.GET.get('guests', 1)

        if check_in:
            initial_data['check_in_date'] = check_in
        if check_out:
            initial_data['check_out_date'] = check_out
        if guests:
            initial_data['guests'] = guests

        form = BookingForm(initial=initial_data)
    
    context = {
        'form': form,
        'room': room,
        'hotel': hotel,
    }
    return render(request, 'booking/booking_form.html', context)

@login_required
@require_POST
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if cancellation is allowed
    if booking.status == BookingStatus.CANCELLED:
        messages.error(request, "This booking is already cancelled.")
    elif booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
        messages.error(request, "Cannot cancel a booking that has already been checked in or out.")
    else:
        booking.cancel()
        messages.success(request, "Your booking has been cancelled successfully.")
    
    return redirect('booking_detail', booking_id=booking.id)

@login_required
def check_room_availability(request):
    """AJAX endpoint to check room availability"""
    room_id = request.GET.get('room_id')
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    
    if not all([room_id, check_in, check_out]):
        return JsonResponse({'error': 'Missing required parameters', 'params': {
            'room_id': room_id, 
            'check_in': check_in, 
            'check_out': check_out
        }}, status=400)
    
    try:
        room = Room.objects.get(id=room_id)
        check_in_date = timezone.datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = timezone.datetime.strptime(check_out, '%Y-%m-%d').date()
        
        # Check that dates are valid
        if check_out_date <= check_in_date:
            return JsonResponse({'error': 'Check-out date must be after check-in date'}, status=400)
        
        if check_in_date < timezone.now().date():
            return JsonResponse({'error': 'Check-in date cannot be in the past'}, status=400)
        
        # Check for overlapping bookings
        overlapping_bookings = Booking.objects.filter(
            room=room,
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date
        ).exclude(status=BookingStatus.CANCELLED)
        
        is_available = not overlapping_bookings.exists()
        
        # Calculate price
        nights = (check_out_date - check_in_date).days
        total_price = room.price * nights
        
        return JsonResponse({
            'available': is_available,
            'nights': nights,
            'total_price': float(total_price)
        })
    except Room.DoesNotExist:
        return JsonResponse({'error': 'Room not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
@login_required
def process_payment(request, booking_id):
    """Process a payment for a booking using Stripe"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is already paid
    if booking.payment_status == 'paid':
        messages.info(request, "This booking is already fully paid.")
        return redirect('booking_detail', booking_id=booking.id)

    # Calculate amount due
    total_paid = Payment.objects.filter(booking=booking, is_refund=False).aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    total_refunded = Payment.objects.filter(booking=booking, is_refund=True).aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    net_paid = total_paid - total_refunded
    amount_due = booking.total_price - net_paid

    if request.method == 'POST':
        try:
            # Get payment intent ID from the form
            payment_intent_id = request.POST.get('payment_intent_id')
            
            if not payment_intent_id:
                messages.error(request, "Payment processing failed. Please try again.")
                return redirect('process_payment', booking_id=booking.id)
            
            # Confirm the payment with Stripe
            payment_data = StripeService.confirm_payment(payment_intent_id)
            
            if not payment_data or payment_data['status'] != 'succeeded':
                messages.error(request, "Payment was not successful. Please try again.")
                return redirect('process_payment', booking_id=booking.id)
            
            # Create the payment record
            payment = Payment.objects.create(
                booking=booking,
                amount=payment_data['amount'],
                transaction_id=payment_intent_id,
                stripe_payment_intent_id=payment_intent_id,
                payment_method='stripe'
            )
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                booking=booking,
                type=NotificationType.PAYMENT_RECEIVED,
                message=f"Your payment of ${payment_data['amount']:.2f} for booking #{booking.id} has been received."
            )

            # If fully paid, update booking status to confirmed if it was pending
            status_changed = booking.update_status_after_payment()
            if status_changed:
                messages.success(request, f"Payment of ${payment_data['amount']:.2f} received — your booking is confirmed!")
            else:
                messages.success(request, f"Payment of ${payment_data['amount']:.2f} has been processed successfully.")
            
            return redirect('booking_detail', booking_id=booking.id)
            
        except Exception as e:
            messages.error(request, f"Payment processing failed: {str(e)}")
            return redirect('process_payment', booking_id=booking.id)
    
    # For GET requests, create payment intent and show the payment form
    payment_intent_data = StripeService.create_payment_intent(booking, amount_due)
    
    if not payment_intent_data:
        messages.error(request, "Unable to process payment at this time. Please try again later.")
        return redirect('booking_detail', booking_id=booking.id)
    
    recent_payments = Payment.objects.filter(booking=booking).order_by('-payment_date')[:5]
    
    context = {
        'booking': booking,
        'amount_due': amount_due,
        'recent_payments': recent_payments,
        'payment_history': booking.payments.all().order_by('-payment_date'),
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'client_secret': payment_intent_data['client_secret'],
        'amount_cents': payment_intent_data['amount_cents'],
    }
    return render(request, 'booking/payment_form.html', context)

@login_required
def payment_history(request, booking_id):
    """View payment history for a booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    payments = booking.payments.all().order_by('-payment_date')
    
    # Calculate totals
    total_paid = payments.filter(is_refund=False).aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    total_refunded = payments.filter(is_refund=True).aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    net_paid = total_paid - total_refunded
    
    context = {
        'booking': booking,
        'payments': payments,
        'total_paid': total_paid,
        'total_refunded': total_refunded,
        'net_paid': net_paid,
        'amount_due': booking.total_price - net_paid,
    }
    return render(request, 'booking/payment_history.html', context)

@login_required
@require_POST
def process_refund(request, booking_id):
    """Process a refund for a cancelled booking using Stripe"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is cancelled
    if booking.status != BookingStatus.CANCELLED:
        messages.error(request, "Only cancelled bookings can be refunded.")
        return redirect('booking_detail', booking_id=booking.id)

    # Calculate amount paid
    total_paid = Payment.objects.filter(booking=booking, is_refund=False).aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    total_refunded = Payment.objects.filter(booking=booking, is_refund=True).aggregate(
        total=models.Sum('amount')
    )['total'] or 0
    
    net_paid = total_paid - total_refunded
    
    if net_paid <= 0:
        messages.error(request, "No refund is available as no payment has been made.")
        return redirect('booking_detail', booking_id=booking.id)
    
    # Determine refund amount based on cancellation policy
    days_until_checkin = (booking.check_in_date - timezone.now().date()).days
    refund_percentage = 0
    
    if days_until_checkin >= 7:
        # Full refund
        refund_percentage = 100
    elif days_until_checkin >= 3:
        # 50% refund
        refund_percentage = 50
    
    if refund_percentage > 0:
        refund_amount = (net_paid * refund_percentage) / 100
        
        # Find the most recent Stripe payment to refund
        stripe_payment = Payment.objects.filter(
            booking=booking, 
            is_refund=False,
            stripe_payment_intent_id__isnull=False
        ).order_by('-payment_date').first()
        
        if stripe_payment and stripe_payment.stripe_payment_intent_id:
            # Process Stripe refund
            refund_data = StripeService.create_refund(
                stripe_payment.stripe_payment_intent_id, 
                refund_amount
            )
            
            if refund_data:
                # Create the refund record
                refund = Payment.objects.create(
                    booking=booking,
                    amount=refund_amount,
                    transaction_id=refund_data['id'],
                    stripe_payment_intent_id=stripe_payment.stripe_payment_intent_id,
                    is_refund=True,
                    payment_method='stripe'
                )
                
                # Update booking payment status
                if refund_amount >= net_paid:
                    booking.payment_status = PaymentStatus.REFUNDED
                    booking.save()
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    booking=booking,
                    type=NotificationType.PAYMENT_RECEIVED,
                    message=f"Your refund of ${refund_amount:.2f} for booking #{booking.id} has been processed."
                )
                
                messages.success(request, f"Refund of ${refund_amount:.2f} has been processed through Stripe.")
            else:
                messages.error(request, "Refund processing failed. Please contact support.")
        else:
            # Fallback for non-Stripe payments (shouldn't happen with new implementation)
            refund = Payment.objects.create(
                booking=booking,
                amount=refund_amount,
                transaction_id=f"REFUND-{booking.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                is_refund=True,
                payment_method='manual'
            )
            
            messages.success(request, f"Refund of ${refund_amount:.2f} has been processed manually.")
    else:
        messages.warning(request, "No refund is available according to the cancellation policy.")
    
    return redirect('booking_detail', booking_id=booking.id)

@login_required
def add_review(request, booking_id):
    """Add a review for a completed booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is eligible for review
    if booking.status != BookingStatus.CHECKED_OUT:
        messages.error(request, "You can only review bookings that have been checked out.")
        return redirect('booking_detail', booking_id=booking_id)
    
    # Check if a review already exists - use try/except with OneToOneField
    try:
        # This will raise an exception if no review exists
        existing_review = booking.review
        messages.info(request, "You have already reviewed this booking.")
        return redirect('edit_review', booking_id=booking_id)
    except Review.DoesNotExist:
        # No review exists, we can continue
        pass
    
    if request.method == 'POST':
        # Don't use a ModelForm with OneToOneField - handle fields manually
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Validate the input
        if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
            messages.error(request, "Please provide a valid rating between 1 and 5.")
            return render(request, 'booking/add_review.html', {
                'booking': booking,
                'hotel': booking.room.hotel,
                'form': ReviewForm(request.POST)
            })
        
        # Create the review manually
        try:
            review = Review(
                booking=booking,
                user=request.user,
                hotel=booking.room.hotel,
                rating=int(rating),
                comment=comment
            )
            review.save()
            
            messages.success(request, "Your review has been submitted successfully. Thank you for your feedback!")
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                booking=booking,
                type=NotificationType.REVIEW_SUBMITTED,
                message=f"Your review for your stay at {booking.room.hotel.name} has been submitted."
            )
            
            return redirect('booking_detail', booking_id=booking_id)
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
    # For GET requests
    form = ReviewForm()
    
    context = {
        'form': form,
        'booking': booking,
        'hotel': booking.room.hotel,
    }
    return render(request, 'booking/add_review.html', context)

@login_required
def edit_review(request, booking_id):
    """Edit an existing review"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Get the review using try/except with OneToOneField
    try:
        review = booking.review
    except Review.DoesNotExist:
        messages.error(request, "No review found for this booking.")
        return redirect('booking_detail', booking_id=booking_id)
    
    if request.method == 'POST':
        # Handle form submission manually
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Validate the input
        if not rating or not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
            messages.error(request, "Please provide a valid rating between 1 and 5.")
        else:
            try:
                # Update the review
                review.rating = int(rating)
                review.comment = comment
                review.save()
                
                messages.success(request, "Your review has been updated successfully.")
                return redirect('booking_detail', booking_id=booking_id)
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    
    # For GET requests
    form = ReviewForm(initial={'rating': review.rating, 'comment': review.comment})
    
    context = {
        'form': form,
        'booking': booking,
        'hotel': booking.room.hotel,
        'review': review,
    }
    return render(request, 'booking/edit_review.html', context)

@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = StripeService.construct_webhook_event(payload, sig_header)
        if not event:
            return JsonResponse({'error': 'Invalid payload'}, status=400)
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            
            # Find the booking from metadata
            booking_id = payment_intent['metadata'].get('booking_id')
            if booking_id:
                try:
                    booking = Booking.objects.get(id=booking_id)
                    
                    # Check if payment already exists
                    existing_payment = Payment.objects.filter(
                        stripe_payment_intent_id=payment_intent['id']
                    ).first()
                    
                    if not existing_payment:
                        # Create payment record
                        Payment.objects.create(
                            booking=booking,
                            amount=payment_intent['amount'] / 100,  # Convert from cents
                            transaction_id=payment_intent['id'],
                            stripe_payment_intent_id=payment_intent['id'],
                            payment_method='stripe'
                        )
                        
                        # Create notification
                        Notification.objects.create(
                            user=booking.user,
                            booking=booking,
                            type=NotificationType.PAYMENT_RECEIVED,
                            message=f"Your payment of ${payment_intent['amount'] / 100:.2f} for booking #{booking.id} has been confirmed."
                        )
                
                except Booking.DoesNotExist:
                    pass
        
        elif event['type'] == 'payment_intent.payment_failed':
            # Handle failed payment
            payment_intent = event['data']['object']
            booking_id = payment_intent['metadata'].get('booking_id')
            
            if booking_id:
                try:
                    booking = Booking.objects.get(id=booking_id)
                    
                    # Create notification about failed payment
                    Notification.objects.create(
                        user=booking.user,
                        booking=booking,
                        type=NotificationType.CUSTOM,
                        message=f"Payment failed for booking #{booking.id}. Please try again."
                    )
                
                except Booking.DoesNotExist:
                    pass
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)