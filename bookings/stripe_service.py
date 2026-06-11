import stripe
from django.conf import settings
from django.urls import reverse
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    """Service class for handling Stripe payments"""
    
    @staticmethod
    def create_payment_intent(booking, amount=None):
        """
        Create a Stripe PaymentIntent for a booking
        
        Args:
            booking: Booking instance
            amount: Payment amount (optional, defaults to amount due)
            
        Returns:
            dict: Payment intent data or None if error
        """
        try:
            # Calculate amount if not provided
            if amount is None:
                from .models import Payment
                from django.db.models import Sum
                
                total_paid = Payment.objects.filter(
                    booking=booking, 
                    is_refund=False
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                total_refunded = Payment.objects.filter(
                    booking=booking, 
                    is_refund=True
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                net_paid = total_paid - total_refunded
                amount = booking.total_price - net_paid
            
            # Convert to cents (Stripe requires amounts in smallest currency unit)
            amount_cents = int(amount * 100)
            
            if amount_cents <= 0:
                return None
                
            # Create PaymentIntent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='usd',
                metadata={
                    'booking_id': booking.id,
                    'user_id': booking.user.id,
                    'hotel_name': booking.room.hotel.name,
                    'room_name': booking.room.name,
                },
                description=f'Payment for booking #{booking.id} at {booking.room.hotel.name}',
                receipt_email=booking.user.email,
            )
            
            return {
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': amount,
                'amount_cents': amount_cents,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            return None
    
    @staticmethod
    def confirm_payment(payment_intent_id):
        """
        Retrieve and confirm a payment intent
        
        Args:
            payment_intent_id: Stripe PaymentIntent ID
            
        Returns:
            dict: Payment intent data or None if error
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                'id': payment_intent.id,
                'status': payment_intent.status,
                'amount': payment_intent.amount / 100,  # Convert back from cents
                'metadata': payment_intent.metadata,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving payment intent: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving payment intent: {str(e)}")
            return None
    
    @staticmethod
    def create_refund(payment_intent_id, amount=None):
        """
        Create a refund for a payment
        
        Args:
            payment_intent_id: Stripe PaymentIntent ID
            amount: Refund amount in dollars (optional, defaults to full refund)
            
        Returns:
            dict: Refund data or None if error
        """
        try:
            refund_data = {
                'payment_intent': payment_intent_id
            }
            
            if amount is not None:
                refund_data['amount'] = int(amount * 100)  # Convert to cents
            
            refund = stripe.Refund.create(**refund_data)
            
            return {
                'id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100,  # Convert back from cents
                'reason': refund.reason,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating refund: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating refund: {str(e)}")
            return None
    
    @staticmethod
    def construct_webhook_event(payload, sig_header):
        """
        Construct and verify a webhook event
        
        Args:
            payload: Request body
            sig_header: Stripe signature header
            
        Returns:
            stripe.Event: Webhook event or None if error
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError:
            logger.error("Invalid payload in webhook")
            return None
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return None