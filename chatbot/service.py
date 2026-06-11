"""
AI chatbot service powered by the Anthropic API (Claude Haiku).

Builds a system prompt with live hotel data from the database (plus the
user's bookings when logged in) so the assistant can answer questions
about this site specifically.
"""
import logging

import anthropic
from django.conf import settings

from hotels.models import Hotel
from bookings.models import Booking

logger = logging.getLogger(__name__)

MODEL = 'claude-haiku-4-5'
MAX_RESPONSE_TOKENS = 600
# Keep cost under control: only the most recent messages are sent
MAX_HISTORY_MESSAGES = 12


def _hotel_context():
    """Compact list of hotels for the system prompt."""
    lines = []
    for hotel in Hotel.objects.prefetch_related('rooms').all()[:80]:
        prices = [room.price for room in hotel.rooms.all()]
        price = f"rooms from ${min(prices)}" if prices else "no rooms listed yet"
        flags = []
        if hotel.is_pet_friendly:
            flags.append('pet-friendly')
        if hotel.is_family_friendly:
            flags.append('family-friendly')
        line = f"- {hotel.name} (id={hotel.id}) | {hotel.city} | {hotel.star_rating} stars | {price}"
        if flags:
            line += f" | {', '.join(flags)}"
        lines.append(line)
    return '\n'.join(lines)


def _booking_context(user):
    """The logged-in user's recent bookings for the system prompt."""
    if not user.is_authenticated:
        return "The user is not logged in."
    bookings = (
        Booking.objects.filter(user=user)
        .select_related('room__hotel')
        .order_by('-created_at')[:5]
    )
    if not bookings:
        return f"The user is logged in as {user.username} and has no bookings yet."
    lines = [f"The user is logged in as {user.username}. Their recent bookings:"]
    for b in bookings:
        lines.append(
            f"- Booking #{b.id}: {b.room.hotel.name} ({b.room.name}), "
            f"{b.check_in_date} to {b.check_out_date}, {b.guests} guests, "
            f"${b.total_price}, status: {b.get_status_display()}, "
            f"payment: {b.get_payment_status_display()}"
        )
    return '\n'.join(lines)


def _build_system_prompt(user):
    return f"""You are the friendly virtual assistant of "Pausa Booking", a hotel booking website.

Your job: help visitors find hotels, understand prices, and use the site. Answer in the same language the user writes in (e.g. Romanian or English). Keep answers short and conversational - 2-4 sentences unless more detail is asked for.

What the site offers:
- Browsing and searching hotels by city, star rating and amenities, with a map view.
- Booking a room: open a hotel page, pick a room and dates, then pay securely by card (Stripe).
- Cancellation policy: full refund if cancelled 7+ days before check-in, 50% refund 3-7 days before, no refund under 3 days.
- A confirmation email with the booking details is sent automatically after each booking.
- When you mention a specific hotel, you may link to it as /hotels/<id>/ (markdown links work).

Hotels currently on the site:
{_hotel_context()}

{_booking_context(user)}

Rules:
- Only discuss topics related to this website, hotels, travel and the user's bookings. For anything else, politely steer the conversation back.
- Never invent hotels, prices or bookings that are not in the data above.
- You cannot create, modify or cancel bookings yourself - guide the user to the right page instead."""


def get_chat_reply(user, history):
    """
    Get the assistant's reply for a conversation.

    history: list of {"role": "user"|"assistant", "content": str}
    Returns (reply_text, error_message) - exactly one is None.
    """
    if not settings.ANTHROPIC_API_KEY:
        return None, "The chatbot is not configured yet (missing API key)."

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_RESPONSE_TOKENS,
            system=_build_system_prompt(user),
            messages=history[-MAX_HISTORY_MESSAGES:],
        )
        reply = next((b.text for b in response.content if b.type == 'text'), '')
        return reply, None
    except anthropic.AuthenticationError:
        logger.error("Chatbot: invalid Anthropic API key")
        return None, "The chatbot is misconfigured. Please contact support."
    except anthropic.RateLimitError:
        return None, "The assistant is a bit busy right now - please try again in a moment."
    except anthropic.APIError:
        logger.exception("Chatbot: Anthropic API error")
        return None, "Something went wrong on the assistant's side. Please try again."
