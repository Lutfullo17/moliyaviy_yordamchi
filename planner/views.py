from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from .models import DayPlan, Task

@login_required
def daily_plan(request):
    date_str = request.GET.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            date = timezone.now().date()
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
        # Vaqtni olish
        start_time_raw = request.POST.get('start_time')
        end_time_raw = request.POST.get('end_time')

        # Vaqt formatini tekshirish va tozalash (24 soatlik formatga majburlash)
        def clean_time(time_str):
            if not time_str:
                return None
            try:
                # Agar brauzer AM/PM yuborsa ham, uni 24 soatlikka o'giradi
                return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                try:
                    # Ba'zi brauzerlar soniya bilan yuborishi mumkin
                    return datetime.strptime(time_str, "%H:%M:%S").time()
                except ValueError:
                    return None

        Task.objects.create(
            day_plan=plan,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            start_time=clean_time(start_time_raw),
            end_time=clean_time(end_time_raw),
            priority=request.POST.get('priority', 'medium'),
            is_important=request.POST.get('is_important') == 'on'
        )
        return redirect(f'/planner/?date={plan.date}')

    return render(request, 'planner/task_form.html', {'plan': plan})

@login_required
def task_update(request, task_id):
    task = get_object_or_404(Task, id=task_id, day_plan__user=request.user)
    
    if request.method == 'POST':
        start_time_raw = request.POST.get('start_time')
        end_time_raw = request.POST.get('end_time')
        
        def clean_time(time_str):
            if not time_str: return None
            try: return datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                try: return datetime.strptime(time_str, "%H:%M:%S").time()
                except ValueError: return None

        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.start_time = clean_time(start_time_raw)
        task.end_time = clean_time(end_time_raw)
        task.priority = request.POST.get('priority', 'medium')
        task.is_important = request.POST.get('is_important') == 'on'
        task.save()
        
        return redirect(f'/planner/?date={task.day_plan.date}')
        
    return render(request, 'planner/task_update.html', {'task': task})

@login_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id, day_plan__user=request.user)
    plan_date = task.day_plan.date
    if request.method == 'POST':
        task.delete()
        return redirect(f'/planner/?date={plan_date}')
    return render(request, 'planner/task_delete.html', {'task': task, 'date': plan_date})

@login_required
def task_update_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, day_plan__user=request.user)
    task.status = 'done' if task.status == 'pending' else 'pending'
    task.save()
    return redirect(f'/planner/?date={task.day_plan.date}')

from django.http import JsonResponse
from datetime import timedelta

@login_required
def upcoming_tasks_api(request):
    """
    Frontend uchun asinxron bildirishnoma API.
    Boshlanishiga 1 soatdan kam vaqt qolgan tasks qaytariladi.
    """
    now = timezone.localtime() # current time with timezone
    today_plan = DayPlan.objects.filter(user=request.user, date=now.date()).first()
    
    upcoming = []
    if today_plan:
        # Hozirgi soat:minut
        current_time = now.time()
        # 1 soat qo'shamiz (tz aware now)
        one_hour_later = (now + timedelta(hours=1)).time()
        
        # Agar soat 23:30 bo'lsa, ertangi kunga o'tib ketish muammosi bo'lmasligi u.n sodda check:
        if one_hour_later < current_time:
             # means we crossed midnight, grab everything today starting from now to 23:59
            tasks = today_plan.tasks.filter(start_time__gte=current_time, status='pending')
        else:
            tasks = today_plan.tasks.filter(start_time__gte=current_time, start_time__lte=one_hour_later, status='pending')
            
        for t in tasks:
            upcoming.append({
                'id': t.id,
                'title': t.title,
                'start_time': t.start_time.strftime('%H:%M') if t.start_time else '',
                'msgBody': f"1 soatdan so'ng sizning '{t.title}' vazifangiz bor esingizdami?"
            })
            
    return JsonResponse({'tasks': upcoming})

@login_required
def today_plan_view(request):
    plan, created = DayPlan.objects.get_or_create(
        user=request.user,
        date=timezone.now().date()
    )
    tasks = plan.tasks.all().order_by('start_time')
    return render(request, 'planner/today.html', {
        'plan': plan,
        'tasks': tasks
    })