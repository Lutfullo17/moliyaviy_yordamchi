from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Category

@login_required
def category_list(request):
    categories = Category.objects.filter(
        user=request.user
    ) | Category.objects.filter(is_default=True)

    categories = categories.order_by('name')

    return render(request, 'categories/list.html', {
        'categories': categories
    })


@login_required
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        limit = request.POST.get('monthly_limit', '0')
        limit_duration = request.POST.get('limit_duration')

        if not name or not name.strip():
            return render(request, 'categories/create.html', {
                'error': 'Name cannot be empty'
            })

        try:
            raw_limit = str(limit).replace(',', '').strip()
            monthly_limit = float(raw_limit) if raw_limit else 0
        except ValueError:
            monthly_limit = 0

        try:
            limit_duration = int(limit_duration) if limit_duration else None
        except ValueError:
            limit_duration = None

        Category.objects.create(
            name=name,
            monthly_limit=monthly_limit,
            limit_duration=limit_duration,
            limit_set_at=timezone.now() if monthly_limit > 0 else None,
            user=request.user,
            is_default=False
        )

        return redirect('categories:list')

    return render(request, 'categories/create.html')


@login_required
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)


    if category.user != request.user:
        return redirect('categories:list')


    if category.is_default:
        return redirect('categories:list')

    if request.method == 'POST':
        name = request.POST.get('name')
        limit = request.POST.get('monthly_limit', '0')
        limit_duration = request.POST.get('limit_duration')

        if not name or not name.strip():
            return render(request, 'categories/create.html', {
                'error': 'Name cannot be empty',
                'category': category
            })

        try:
            raw_limit = str(limit).replace(',', '').strip()
            monthly_limit = float(raw_limit) if raw_limit else 0
        except ValueError:
            monthly_limit = 0

        try:
            limit_duration = int(limit_duration) if limit_duration else None
        except ValueError:
            limit_duration = None

        category.name = name
        
        # Agar limit summasi yoki muddati o'zgarsa, vaqtni yangilaymiz
        if float(category.monthly_limit) != monthly_limit or category.limit_duration != limit_duration:
            if monthly_limit > 0:
                category.limit_set_at = timezone.now()
            else:
                category.limit_set_at = None
        
        category.monthly_limit = monthly_limit
        category.limit_duration = limit_duration
        category.save()

        return redirect('categories:list')

    return render(request, 'categories/create.html', {
        'category': category
    })


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)


    if category.user != request.user:
        return redirect('categories:list')


    if category.is_default:
        return redirect('categories:list')

    if request.method == 'POST':
        category.delete()
        return redirect('categories:list')

    return render(request, 'categories/delete.html', {
        'category': category
    })