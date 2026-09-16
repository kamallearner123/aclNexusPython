def unread_messages_context(request):
    """
    Context processor providing unread direct message count across all teams.
    """
    if request.user.is_authenticated:
        try:
            from .models import DirectMessage
            count = DirectMessage.objects.filter(recipient=request.user, is_read=False).count()
            return {'unread_team_messages_count': count}
        except Exception:
            return {'unread_team_messages_count': 0}
    return {'unread_team_messages_count': 0}
