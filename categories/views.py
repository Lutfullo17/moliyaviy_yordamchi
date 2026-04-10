from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
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

        if not name or not name.strip():
            return render(request, 'categories/create.html', {
                'error': 'Name cannot be empty'
            })

        try:
            raw_limit = str(limit).replace(',', '').strip()
            monthly_limit = float(raw_limit) if raw_limit else 0
        except ValueError:
            monthly_limit = 0

        Category.objects.create(
            name=name,
            monthly_limit=monthly_limit,
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

        category.name = name
        category.monthly_limit = monthly_limit
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