from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ReminderForm
from .models import Reminder


@login_required
def reminder_list(request):
    reminders = Reminder.objects.filter(user=request.user).order_by('remind_time')
    return render(request, 'reminders/list.html', {'reminders': reminders})


@login_required
def reminder_create(request):
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            return redirect('reminders:list')
    else:
        form = ReminderForm()

    return render(request, 'reminders/create.html', {'form': form})


@login_required
def reminder_toggle(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    reminder.is_done = not reminder.is_done
    reminder.save()
    return redirect('reminders:list')


@login_required
def reminder_delete(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    if request.method == 'POST':
        reminder.delete()
    return redirect('reminders:list')
