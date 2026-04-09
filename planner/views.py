from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .models import DayPlan, Task


@method_decorator(csrf_exempt, name='dispatch')
class TodayPlanView(View):
    def get(self, request):
        today = timezone.now().date()
        plan, created = DayPlan.objects.get_or_create(
            user=request.user,
            date=today
        )
        tasks = list(plan.tasks.values())
        return JsonResponse({
            'id': plan.id,
            'date': str(plan.date),
            'created': created,
            'tasks': tasks
        })


@method_decorator(csrf_exempt, name='dispatch')
class PlanByDateView(View):

    def get(self, request):
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'date parametri kerak'}, status=400)

        plan, created = DayPlan.objects.get_or_create(
            user=request.user,
            date=date_str
        )
        tasks = list(plan.tasks.values())
        return JsonResponse({
            'id': plan.id,
            'date': str(plan.date),
            'created': created,
            'tasks': tasks
        })


@method_decorator(csrf_exempt, name='dispatch')
class TaskListCreateView(View):

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON xato'}, status=400)

        title = data.get('title', '').strip()
        if not title:
            return JsonResponse({'error': "title bo'sh bo'lmasin"}, status=400)

        date_str = data.get('date', str(timezone.now().date()))

        plan, _ = DayPlan.objects.get_or_create(
            user=request.user,
            date=date_str
        )

        task = Task.objects.create(
            day_plan=plan,
            title=title,
            description=data.get('description', ''),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium'),
            is_important=data.get('is_important', False),
        )

        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'priority': task.priority,
            'is_important': task.is_important,
            'day_plan_id': task.day_plan_id,
        }, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class TaskDetailView(View):
    """PATCH /tasks/:id/   DELETE /tasks/:id/"""

    def get_task(self, task_id, user):
        return get_object_or_404(Task, id=task_id, day_plan__user=user)

    def patch(self, request, task_id):
        task = self.get_task(task_id, request.user)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON xato'}, status=400)

        allowed_fields = ['title', 'description', 'start_time',
                          'end_time', 'status', 'priority', 'is_important']
        for field in allowed_fields:
            if field in data:
                setattr(task, field, data[field])

        if 'title' in data and not data['title'].strip():
            return JsonResponse({'error': "title bo'sh bo'lmasin"}, status=400)

        task.save()
        return JsonResponse({
            'id': task.id,
            'title': task.title,
            'status': task.status,
            'priority': task.priority,
        })

    def delete(self, request, task_id):
        task = self.get_task(task_id, request.user)
        task.delete()
        return JsonResponse({'message': "Task o'chirildi"})