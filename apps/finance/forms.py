from django import forms

from .models import Expense, Income


class _Base(forms.ModelForm):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for f in self.fields.values():
            if not isinstance(f.widget, forms.CheckboxInput):
                f.widget.attrs.setdefault('class', 'inp')
            if isinstance(f.widget, forms.DateInput):
                f.widget.input_type = 'date'
                f.widget.format = '%Y-%m-%d'
            if isinstance(f.widget, forms.Textarea):
                f.widget.attrs['rows'] = 3


class IncomeForm(_Base):
    class Meta:
        model = Income
        fields = ['title', 'client', 'source', 'total_amount', 'received', 'date', 'due_date', 'note']
        widgets = {'date': forms.DateInput(), 'due_date': forms.DateInput()}

    def clean(self):
        d = super().clean()
        t, r = d.get('total_amount'), d.get('received')
        if t is not None and r is not None and r > t:
            self.add_error('received', 'Received cannot be more than the total amount.')
        return d


class ExpenseForm(_Base):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'spent_at', 'amount', 'date', 'note']
        widgets = {'date': forms.DateInput()}
