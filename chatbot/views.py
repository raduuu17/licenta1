import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .service import get_chat_reply

SESSION_KEY = 'chatbot_history'
# Hard cap on stored history so the session doesn't grow forever
MAX_STORED_MESSAGES = 20


@require_POST
def chat_message(request):
    """Receive a user message and return the assistant's reply (JSON)."""
    try:
        data = json.loads(request.body)
        message = (data.get('message') or '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    if not message:
        return JsonResponse({'error': 'Message is empty.'}, status=400)
    if len(message) > 1000:
        return JsonResponse({'error': 'Message is too long (max 1000 characters).'}, status=400)

    history = request.session.get(SESSION_KEY, [])
    history.append({'role': 'user', 'content': message})

    reply, error = get_chat_reply(request.user, history)
    if error:
        # Don't keep the failed turn in history
        history.pop()
        request.session[SESSION_KEY] = history
        return JsonResponse({'error': error}, status=503)

    history.append({'role': 'assistant', 'content': reply})
    request.session[SESSION_KEY] = history[-MAX_STORED_MESSAGES:]

    return JsonResponse({'reply': reply})


@require_POST
def chat_reset(request):
    """Clear the conversation history."""
    request.session[SESSION_KEY] = []
    return JsonResponse({'ok': True})


@require_GET
def chat_history(request):
    """Return the conversation history so the widget can restore it between pages."""
    return JsonResponse({'messages': request.session.get(SESSION_KEY, [])})
