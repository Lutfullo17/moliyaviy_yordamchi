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
import random

@login_required
def ai_recommend_view(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    
    # AI Logikasi simulyatsiyasi (Buni keyinchalik Gemini/OpenAI API ga ulash mumkin)
    remaining_amount = goal.target_amount - goal.current_amount
    days_left = (goal.deadline - timezone.now().date()).days
    
    if days_left > 0:
        daily_needed = remaining_amount / days_left
        monthly_needed = daily_needed * 30
    else:
        daily_needed = 0
        monthly_needed = 0

    recommendations = []
    
    if remaining_amount <= 0:
        advice = "Tabriklaymiz! Siz maqsadingizga to'liq yetdingiz! Yana biror yangi cho'qqini zabt etamizmi?"
    elif days_left < 0:
        advice = f"Afsuski, muddat tugagan. Sizga yana {remaining_amount:,.0f} UZS yetmayapti. Iltimos, muddatni orqaga suring yoki jiddiy cheklovlar qiling."
    else:
        # Generate some smart tips
        if daily_needed > 500000:
            recommendations.append("Sizning maqsadingiz juda katta summa talab qiladi. Qo'shimcha daromad manbalarini (freelance, investitsiya) qidirib ko'ring.")
        elif daily_needed > 100000:
            recommendations.append(f"Kuniga xarajatlarni to'g'ri rejalashtiring. Fast-food va keraksiz kofe sotib olishdan voz kechish har oy sizga ko'p yordam beradi.")
        else:
            recommendations.append("Siz juda yaxshi ketmoqdasiz! Oddiy kundalik tejamkorlik usullari maqsadga yetish uchun yetarli bo'ladi.")
            
        recommendations.append(f"Statistikaga ko'ra, siz har oy qariyb {monthly_needed:,.0f} UZS saqlashingiz kerak. Buni amalga oshirish uchun 'Avtomatik O'tkazmalar' yoqing.")
        
        advice = f"AI Tahlili: {goal.title} maqsadi sari muddat tugashiga {days_left} kun qoldi. Qolgan summa {remaining_amount:,.0f} UZS. Siz kuniga o'rtacha {daily_needed:,.0f} UZS yig'ishingiz zarur."

    context = {
        'goal': goal,
        'advice': advice,
        'recommendations': recommendations,
        'days_left': days_left,
        'daily_needed': daily_needed
    }
    return render(request, 'goals/ai_recommendation.html', context)