# planner/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import DayPlan, Task


@login_required
def daily_plan(request):
    # Agar sana berilmagan bo'lsa, bugunni oladi
    date_str = request.GET.get('date')
    if date_str:
        date = date_str
    else:
        date = timezone.now().date()

    plan, created = DayPlan.objects.get_or_create(
        user=request.user,
        date=date
    )
    tasks = plan.tasks.all().order_by('start_time')

    return render(request, 'planner/plan_detail.html', {
        'plan': plan,
        'tasks': tasks,
        'date': date
    })


@login_required
def task_create(request, plan_id):
    plan = get_object_or_404(DayPlan, id=plan_id, user=request.user)
    if request.method == 'POST':
        Task.objects.create(
            day_plan=plan,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            start_time=request.POST.get('start_time') or None,
            end_time=request.POST.get('end_time') or None,
            priority=request.POST.get('priority', 'medium'),
            is_important=request.POST.get('is_important') == 'on'
        )
        return redirect(f'/planner/?date={plan.date}')
    return render(request, 'planner/task_form.html', {'plan': plan})


@login_required
def task_update_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, day_plan__user=request.user)
    task.status = 'done' if task.status == 'pending' else 'pending'
    task.save()
    return redirect(f'/planner/?date={task.day_plan.date}')

