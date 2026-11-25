from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Expense, Income


class FinanceReportTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='finance-staff',
            password='Secure-test-password-2026',
            is_staff=True,
        )
        self.url = reverse('dashboard:finance_report_pdf')

    def test_pdf_report_requires_staff_access(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/login/', response['Location'])

        get_user_model().objects.create_user(username='regular-user', password='Secure-test-password-2026')
        self.client.login(username='regular-user', password='Secure-test-password-2026')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_staff_can_download_complete_finance_report(self):
        Income.objects.create(
            title='Website project income',
            client='Acme Client',
            source='direct',
            total_amount=100000,
            received=60000,
        )
        Expense.objects.create(
            title='Hosting bill',
            category='hosting',
            spent_at='Example Host',
            amount=12000,
        )
        self.client.force_login(self.staff)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="income-expenses-', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertIn(b'Income and Expenses - Financial Report', response.content)

    def test_finance_screen_has_pdf_download_action(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('dashboard:finance'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('dashboard:finance_report_pdf'))
        self.assertContains(response, 'Download PDF report')


class AvailableBalanceTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(username='fin2', password='Secure-test-password-2026', is_staff=True)
        self.client.force_login(self.staff)

    def test_available_is_received_minus_spent(self):
        from . import stats
        Income.objects.create(title='A', client='X', source='direct', total_amount=100000, received=60000)
        Income.objects.create(title='B', client='Y', source='direct', total_amount=50000, received=10000)
        Expense.objects.create(title='Hosting', category='hosting', amount=12000)
        s = stats.summary()
        self.assertEqual(s['available'], 58000)
        self.assertEqual(s['pending'], 80000)
        r = self.client.get(reverse('dashboard:finance'))
        self.assertContains(r, 'Available in account')
        self.assertContains(r, 'Rs 58,000')
        self.assertContains(self.client.get(reverse('dashboard:overview')), 'Available in account')

    def test_negative_balance_is_flagged(self):
        Expense.objects.create(title='Laptop', category='hosting', amount=5000)
        r = self.client.get(reverse('dashboard:finance'))
        self.assertContains(r, 'is-neg')
        self.assertContains(r, 'spending is more than received')

    def test_empty_state_is_zero(self):
        self.assertContains(self.client.get(reverse('dashboard:finance')), 'Rs 0')
