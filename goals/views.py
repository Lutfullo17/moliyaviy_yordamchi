from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Goal
from .forms import GoalForm

@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user)
    return render(request, 'goals/list.html', {'goals': goals})

@login_required
def goal_create(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('goals:list')
    else:
        form = GoalForm()
    return render(request, 'goals/create.html', {'form': form})

@login_required
def goal_update(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            return redirect('goals:list')
    else:
        form = GoalForm(instance=goal)
    return render(request, 'goals/create.html', {'form': form, 'goal': goal})

@login_required
def goal_delete(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.delete()
        return redirect('goals:list')
    return render(request, 'goals/delete.html', {'goal': goal})

from django.utils import timezone

from .services.gemini_service import get_ai_advice


@login_required
def ai_recommend_view(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)

    remaining_amount = goal.target_amount - goal.current_amount
    days_left = (goal.deadline - timezone.now().date()).days

    if days_left > 0:
        daily_needed = remaining_amount / days_left
    else:
        daily_needed = remaining_amount

    from django.core.cache import cache
    cache_key = f"ai_advice_{goal.id}_{goal.current_amount}_{goal.target_amount}"
    cached_data = cache.get(cache_key)

    if cached_data:
        advice, recommendations = cached_data
    else:
        try:
            advice, recommendations = get_ai_advice(goal, daily_needed, max(days_left, 0))
            cache.set(cache_key, (advice, recommendations), 60 * 60 * 24)  # Cache for 24 hours
        except Exception as e:
            advice = "AI xizmatida xatolik yuz berdi"
            recommendations = [f"Xatolik: {str(e)}", "Iltimos, keyinroq urinib ko'ring oki API kalitni tekshiring."]

    return render(request, 'goals/ai_recommendation.html', {
        "goal": goal,
        "advice": advice,
        "recommendations": recommendations,
        "days_left": days_left,
        "daily_needed": daily_needed,
    })