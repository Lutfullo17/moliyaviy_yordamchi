# reminders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Reminder

@login_required
def reminder_list(request):
    reminders = Reminder.objects.filter(user=request.user).order_by('remind_time')
    return render(request, 'reminders/list.html', {'reminders': reminders})

@login_required
def reminder_create(request):
    if request.method == 'POST':
        Reminder.objects.create(
            user=request.user,
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            remind_time=request.POST.get('remind_time')
        )
        return redirect('reminders:list')
    return render(request, 'reminders/create.html')