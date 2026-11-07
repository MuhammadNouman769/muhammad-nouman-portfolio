from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.dashboard.views import render_dash, staff_required

from . import stats
from .forms import ExpenseForm, IncomeForm
from .models import Expense, Income

KINDS = {
    'income': (Income, IncomeForm, 'Income'),
    'expense': (Expense, ExpenseForm, 'Expense'),
}


@staff_required
def finance_home(request):
    q = request.GET.get('q', '').strip()
    incomes, expenses = Income.objects.all(), Expense.objects.all()
    if q:
        incomes = incomes.filter(Q(title__icontains=q) | Q(client__icontains=q))
        expenses = expenses.filter(Q(title__icontains=q) | Q(spent_at__icontains=q) | Q(note__icontains=q))
    return render_dash(request, 'finance/finance.html', {
        'active': 'finance', 'q': q, 's': stats.summary(), 'sources': stats.by_source(),
        'categories': stats.by_category(), 'months': stats.monthly(),
        'incomes': incomes[:100], 'expenses': expenses[:100],
    })


@staff_required
def finance_edit(request, kind, pk=None):
    if kind not in KINDS:
        return redirect('dashboard:finance')
    model, form_cls, label = KINDS[kind]
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = form_cls(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{label} saved.')
        return redirect('dashboard:finance')
    return render_dash(request, 'finance/finance_form.html', {
        'active': 'finance', 'form': form, 'kind': kind, 'label': label, 'obj': obj})


@staff_required
@require_POST
def finance_delete(request, kind, pk):
    if kind in KINDS:
        get_object_or_404(KINDS[kind][0], pk=pk).delete()
        messages.success(request, f'{KINDS[kind][2]} deleted.')
    return redirect('dashboard:finance')
