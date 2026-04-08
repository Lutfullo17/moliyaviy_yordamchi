from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Reminder


@method_decorator(csrf_exempt, name='dispatch')
class ReminderListCreateView(View):
    """GET /reminders/   POST /reminders/"""

    def get(self, request):
        reminders = Reminder.objects.filter(user=request.user).values()
        return JsonResponse(list(reminders), safe=False)

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON xato'}, status=400)

        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': "title bo'sh bo'lmasin"}, status=400)

        remind_time = data.get('remind_time')
        if not remind_time:
            return JsonResponse({'error': 'remind_time kerak'}, status=400)

        reminder = Reminder.objects.create(
            user=request.user,
            title=title,
            description=data.get('description', ''),
            remind_time=remind_time,
            is_done=data.get('is_done', False),
        )

        return JsonResponse({
            'id': reminder.id,
            'title': reminder.title,
            'remind_time': str(reminder.remind_time),
            'is_done': reminder.is_done,
        }, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class ReminderDetailView(View):
    """PATCH /reminders/:id/   DELETE /reminders/:id/"""

    def get_reminder(self, reminder_id, user):
        return get_object_or_404(Reminder, id=reminder_id, user=user)

    def patch(self, request, reminder_id):
        reminder = self.get_reminder(reminder_id, request.user)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON xato'}, status=400)

        allowed_fields = ['title', 'description', 'remind_time', 'is_done']
        for field in allowed_fields:
            if field in data:
                setattr(reminder, field, data[field])

        if 'title' in data and not data['title'].strip():
            return JsonResponse({'error': "title bo'sh bo'lmasin"}, status=400)

        reminder.save()
        return JsonResponse({
            'id': reminder.id,
            'title': reminder.title,
            'is_done': reminder.is_done,
        })

    def delete(self, request, reminder_id):
        reminder = self.get_reminder(reminder_id, request.user)
        reminder.delete()
        return JsonResponse({'message': "Reminder o'chirildi"})