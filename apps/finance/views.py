from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
def finance_report_pdf(request):
    buffer = BytesIO()
    today = timezone.localdate()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title='Income and Expenses Report',
        author='Portfolio Dashboard',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='ReportSubtitle', parent=styles['Normal'], textColor=colors.HexColor('#64708f'),
        fontSize=9, leading=13, spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name='ReportSection', parent=styles['Heading2'], textColor=colors.HexColor('#171447'),
        fontSize=13, leading=17, spaceBefore=12, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        name='ReportCell', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5,
        leading=9.5, textColor=colors.HexColor('#15172e'),
    ))
    styles.add(ParagraphStyle(
        name='ReportHeaderCell', parent=styles['ReportCell'], fontName='Helvetica-Bold',
        textColor=colors.white,
    ))
    styles.add(ParagraphStyle(
        name='ReportAmount', parent=styles['ReportCell'], alignment=TA_RIGHT,
    ))

    def cell(value, style='ReportCell'):
        return Paragraph(escape(str(value if value is not None else '')), styles[style])

    def amount(value):
        return f'Rs {value:,.0f}'

    story = [
        Paragraph('Income &amp; Expenses Report', styles['Title']),
        Paragraph(f'Complete financial ledger · Generated {today:%d %b %Y}', styles['ReportSubtitle']),
    ]

    summary = stats.summary()
    summary_data = [[
        cell('Agreed income', 'ReportHeaderCell'),
        cell('Received', 'ReportHeaderCell'),
        cell('Outstanding', 'ReportHeaderCell'),
        cell('Expenses', 'ReportHeaderCell'),
        cell('Net in hand', 'ReportHeaderCell'),
    ], [
        cell(amount(summary['total'])),
        cell(amount(summary['received'])),
        cell(amount(summary['pending'])),
        cell(amount(summary['spent'])),
        cell(amount(summary['net'])),
    ]]
    summary_table = Table(summary_data, colWidths=[49 * mm] * 5, hAlign='LEFT')
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#171447')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f2f3fb')),
        ('BOX', (0, 0), (-1, -1), .5, colors.HexColor('#d9dced')),
        ('INNERGRID', (0, 0), (-1, -1), .35, colors.HexColor('#d9dced')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.extend([summary_table, Spacer(1, 5 * mm)])

    source_rows = stats.by_source()
    category_rows = stats.by_category()
    if source_rows or category_rows:
        story.append(Paragraph('Breakdown', styles['ReportSection']))
        breakdown_data = [[
            cell('Income source', 'ReportHeaderCell'), cell('Deals', 'ReportHeaderCell'),
            cell('Agreed', 'ReportHeaderCell'), cell('Received', 'ReportHeaderCell'),
            cell('Expense category', 'ReportHeaderCell'), cell('Payments', 'ReportHeaderCell'),
            cell('Spent', 'ReportHeaderCell'),
        ]]
        for index in range(max(len(source_rows), len(category_rows))):
            source = source_rows[index] if index < len(source_rows) else None
            category = category_rows[index] if index < len(category_rows) else None
            breakdown_data.append([
                cell(source['label'] if source else '—'),
                cell(source['n'] if source else '—'),
                cell(amount(source['total']) if source else '—'),
                cell(amount(source['got']) if source else '—'),
                cell(category['label'] if category else '—'),
                cell(category['n'] if category else '—'),
                cell(amount(category['total']) if category else '—'),
            ])
        breakdown_table = Table(
            breakdown_data,
            colWidths=[42 * mm, 18 * mm, 31 * mm, 31 * mm, 48 * mm, 20 * mm, 31 * mm],
            repeatRows=1,
            hAlign='LEFT',
        )
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5b4bf5')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f8fc')]),
            ('BOX', (0, 0), (-1, -1), .4, colors.HexColor('#d9dced')),
            ('INNERGRID', (0, 0), (-1, -1), .3, colors.HexColor('#e2e5ef')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.extend([breakdown_table, Spacer(1, 4 * mm)])

    incomes = Income.objects.all().order_by('-date', '-id')
    story.append(Paragraph(f'Income &amp; Client Payments ({incomes.count()})', styles['ReportSection']))
    income_data = [[
        cell('#', 'ReportHeaderCell'), cell('Deal', 'ReportHeaderCell'),
        cell('Client / source', 'ReportHeaderCell'), cell('Date', 'ReportHeaderCell'),
        cell('Agreed', 'ReportHeaderCell'), cell('Received', 'ReportHeaderCell'),
        cell('Balance', 'ReportHeaderCell'), cell('Status', 'ReportHeaderCell'),
    ]]
    for index, income in enumerate(incomes.iterator(), start=1):
        status = {'paid': 'Paid', 'partial': 'Part paid', 'pending': 'Pending'}[income.status]
        income_data.append([
            cell(index), cell(income.title), cell(f'{income.client or "—"} / {income.get_source_display()}'),
            cell(income.date.strftime('%d %b %Y')), cell(amount(income.total_amount)),
            cell(amount(income.received)), cell(amount(income.remaining)), cell(status),
        ])
    if len(income_data) == 1:
        income_data.append([cell('No income records.')]+[cell('') for _ in range(7)])
    income_table = Table(
        income_data,
        colWidths=[10 * mm, 52 * mm, 52 * mm, 25 * mm, 28 * mm, 28 * mm, 28 * mm, 25 * mm],
        repeatRows=1,
        hAlign='LEFT',
    )
    income_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#171447')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f8fc')]),
        ('BOX', (0, 0), (-1, -1), .4, colors.HexColor('#d9dced')),
        ('INNERGRID', (0, 0), (-1, -1), .3, colors.HexColor('#e2e5ef')),
        ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([income_table, Spacer(1, 4 * mm)])

    expenses = Expense.objects.all().order_by('-date', '-id')
    story.append(Paragraph(f'Expenses ({expenses.count()})', styles['ReportSection']))
    expense_data = [[
        cell('#', 'ReportHeaderCell'), cell('Expense', 'ReportHeaderCell'),
        cell('Category', 'ReportHeaderCell'), cell('Paid to', 'ReportHeaderCell'),
        cell('Date', 'ReportHeaderCell'), cell('Amount', 'ReportHeaderCell'),
    ]]
    for index, expense in enumerate(expenses.iterator(), start=1):
        expense_data.append([
            cell(index), cell(expense.title), cell(expense.get_category_display()),
            cell(expense.spent_at or '—'), cell(expense.date.strftime('%d %b %Y')),
            cell(amount(expense.amount), 'ReportAmount'),
        ])
    if len(expense_data) == 1:
        expense_data.append([cell('No expense records.')]+[cell('') for _ in range(5)])
    expense_table = Table(
        expense_data,
        colWidths=[10 * mm, 62 * mm, 48 * mm, 52 * mm, 28 * mm, 32 * mm],
        repeatRows=1,
        hAlign='LEFT',
    )
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#171447')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f8fc')]),
        ('BOX', (0, 0), (-1, -1), .4, colors.HexColor('#d9dced')),
        ('INNERGRID', (0, 0), (-1, -1), .3, colors.HexColor('#e2e5ef')),
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(expense_table)

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d9dced'))
        canvas.line(doc.leftMargin, 11 * mm, doc.pagesize[0] - doc.rightMargin, 11 * mm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64708f'))
        canvas.drawString(doc.leftMargin, 7 * mm, f'Confidential · Generated {today:%d %b %Y}')
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 7 * mm, f'Page {doc.page}')
        canvas.restoreState()

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="income-expenses-{today:%Y-%m-%d}.pdf"'
    return response


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
