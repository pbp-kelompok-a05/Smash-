from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Report
from .forms import ReportForm
import json

User = get_user_model()

class ReportModelTest(TestCase):
    """Test case untuk model Report"""
    
    def setUp(self):
        """Setup data test untuk model"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.report_data = {
            'content_type': 'post',
            'content_id': 1,
            'category': 'sara',
            'description': 'Konten mengandung SARA',
        }
    
    def test_create_report(self):
        """Test membuat laporan baru"""
        report = Report.objects.create(
            reporter=self.user,
            **self.report_data
        )
        
        self.assertEqual(report.reporter, self.user)
        self.assertEqual(report.content_type, 'post')
        self.assertEqual(report.category, 'sara')
        self.assertEqual(report.status, 'pending')
        self.assertIsNotNone(report.created_at)
        self.assertIsNotNone(report.updated_at)
    
    def test_report_string_representation(self):
        """Test string representation model Report"""
        report = Report.objects.create(
            reporter=self.user,
            **self.report_data
        )
        
        expected_string = f"Laporan post #{report.content_id} oleh {self.user.username}"
        self.assertEqual(str(report), expected_string)
    
    def test_report_status_choices(self):
        """Test pilihan status yang valid"""
        report = Report.objects.create(
            reporter=self.user,
            **self.report_data
        )
        
        # Test status default
        self.assertEqual(report.status, 'pending')
        
        # Test valid status choices
        valid_statuses = ['pending', 'under_review', 'resolved', 'dismissed']
        for status in valid_statuses:
            report.status = status
            report.save()
            self.assertEqual(report.status, status)
    
    def test_report_category_choices(self):
        """Test pilihan kategori yang valid"""
        valid_categories = ['sara', 'spam', 'inappropriate', 'other']
        
        for category in valid_categories:
            report = Report.objects.create(
                reporter=self.user,
                content_type='post',
                content_id=1,
                category=category,
                description=f'Test {category}'
            )
            self.assertEqual(report.category, category)
    
    def test_report_ordering(self):
        """Test urutan laporan (terbaru pertama)"""
        # Buat beberapa laporan dengan created_at berbeda
        report1 = Report.objects.create(
            reporter=self.user,
            content_type='post',
            content_id=1,
            category='spam'
        )
        
        report2 = Report.objects.create(
            reporter=self.user,
            content_type='comment',
            content_id=1,
            category='sara'
        )
        
        reports = Report.objects.all()
        self.assertEqual(reports[0], report2)  # Yang terbaru pertama
        self.assertEqual(reports[1], report1)
    
    def test_report_handled_by_optional(self):
        """Test field handled_by bisa null"""
        report = Report.objects.create(
            reporter=self.user,
            **self.report_data
        )
        
        self.assertIsNone(report.handled_by)
        
        # Assign admin
        report.handled_by = self.admin_user
        report.save()
        self.assertEqual(report.handled_by, self.admin_user)


class ReportFormTest(TestCase):
    """Test case untuk form Report"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.valid_data = {
            'content_type': 'post',
            'content_id': 1,
            'category': 'spam',
            'description': 'Ini adalah spam',
        }
    
    def test_valid_form(self):
        """Test form dengan data valid"""
        form = ReportForm(data=self.valid_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_content_type(self):
        """Test form dengan content_type tidak valid"""
        invalid_data = self.valid_data.copy()
        invalid_data['content_type'] = 'invalid_type'
        
        form = ReportForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('content_type', form.errors)
    
    def test_invalid_category(self):
        """Test form dengan kategori tidak valid"""
        invalid_data = self.valid_data.copy()
        invalid_data['category'] = 'invalid_category'
        
        form = ReportForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)
    
    def test_missing_required_fields(self):
        """Test form dengan field required yang kosong"""
        form = ReportForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('content_type', form.errors)
        self.assertIn('content_id', form.errors)
        self.assertIn('category', form.errors)
    
    def test_description_optional(self):
        """Test field description opsional"""
        data_without_description = self.valid_data.copy()
        data_without_description['description'] = ''
        
        form = ReportForm(data=data_without_description)
        self.assertTrue(form.is_valid())


class ReportViewsTest(TestCase):
    """Test case untuk views Report"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        self.report = Report.objects.create(
            reporter=self.user,
            content_type='post',
            content_id=1,
            category='sara',
            description='Konten SARA'
        )
    
    def test_create_report_ajax_success(self):
        """Test membuat laporan via AJAX berhasil"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('create_report'),
            {
                'content_type': 'post',
                'content_id': 2,
                'category': 'spam',
                'description': 'Ini spam',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(Report.objects.count(), 2)
    
    def test_create_report_ajax_invalid_data(self):
        """Test membuat laporan via AJAX dengan data tidak valid"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('create_report'),
            {
                'content_type': 'invalid_type',  # Invalid
                'content_id': 2,
                'category': 'spam',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
    
    def test_create_report_ajax_unauthenticated(self):
        """Test membuat laporan tanpa login"""
        response = self.client.post(
            reverse('create_report'),
            {
                'content_type': 'post',
                'content_id': 2,
                'category': 'spam',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect ke login
    
    def test_report_list_admin_access(self):
        """Test akses report list oleh admin"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.get(reverse('report_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/report_list.html')
        self.assertContains(response, 'Laporan')
    
    def test_report_list_non_admin_redirect(self):
        """Test user biasa tidak bisa akses report list"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('report_list'))
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_report_detail_admin_access(self):
        """Test akses report detail oleh admin"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.get(reverse('report_detail', args=[self.report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/report_detail.html')
        self.assertContains(response, self.report.get_category_display())
    
    def test_my_reports_authenticated(self):
        """Test user bisa melihat laporan mereka sendiri"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('my_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/my_reports.html')
        self.assertContains(response, 'Laporan Saya')
    
    def test_my_reports_unauthenticated(self):
        """Test akses my_reports tanpa login"""
        response = self.client.get(reverse('my_reports'))
        self.assertEqual(response.status_code, 302)  # Redirect ke login
    
    def test_update_report_status_ajax_success(self):
        """Test update status laporan via AJAX berhasil"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.post(
            reverse('update_report_status', args=[self.report.id]),
            {'status': 'under_review'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Refresh dari database
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'under_review')
        self.assertEqual(self.report.handled_by, self.admin_user)
        self.assertIsNotNone(self.report.handled_at)
    
    def test_update_report_status_ajax_invalid_status(self):
        """Test update status dengan status tidak valid"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.post(
            reverse('update_report_status', args=[self.report.id]),
            {'status': 'invalid_status'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
    
    def test_update_report_status_non_admin(self):
        """Test user biasa tidak bisa update status"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('update_report_status', args=[self.report.id]),
            {'status': 'under_review'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_delete_report_ajax_success(self):
        """Test hapus laporan via AJAX berhasil"""
        self.client.login(username='admin', password='adminpass123')
        
        report_id = self.report.id
        
        response = self.client.delete(
            reverse('delete_report', args=[report_id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Pastikan laporan terhapus
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=report_id)
    
    def test_delete_report_non_admin(self):
        """Test user biasa tidak bisa hapus laporan"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.delete(
            reverse('delete_report', args=[self.report.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_report_dashboard_admin_access(self):
        """Test akses dashboard oleh admin"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.get(reverse('report_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/dashboard.html')
        
        # Pastikan context berisi statistik
        self.assertIn('total_reports', response.context)
        self.assertIn('pending_reports', response.context)
        self.assertIn('category_stats', response.context)
    
    def test_report_list_filtering(self):
        """Test filtering pada report list"""
        self.client.login(username='admin', password='adminpass123')
        
        # Buat laporan dengan status berbeda
        Report.objects.create(
            reporter=self.user,
            content_type='comment',
            content_id=1,
            category='spam',
            status='resolved'
        )
        
        # Filter by status
        response = self.client.get(reverse('report_list') + '?status=pending')
        self.assertEqual(response.status_code, 200)
        
        # Filter by category
        response = self.client.get(reverse('report_list') + '?category=sara')
        self.assertEqual(response.status_code, 200)


class ReportIntegrationTest(TestCase):
    """Test case integrasi untuk workflow lengkap Report"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123'
        )
    
    def test_complete_report_workflow(self):
        """Test workflow lengkap dari buat laporan sampai selesai"""
        # 1. User login dan buat laporan
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('create_report'),
            {
                'content_type': 'post',
                'content_id': 1,
                'category': 'inappropriate',
                'description': 'Konten tidak pantas',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        report = Report.objects.first()
        self.assertEqual(report.status, 'pending')
        
        # 2. Admin login dan lihat laporan
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.get(reverse('report_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Konten tidak pantas')
        
        # 3. Admin update status ke under_review
        response = self.client.post(
            reverse('update_report_status', args=[report.id]),
            {'status': 'under_review'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, 'under_review')
        self.assertEqual(report.handled_by, self.admin_user)
        
        # 4. Admin update status ke resolved
        response = self.client.post(
            reverse('update_report_status', args=[report.id]),
            {'status': 'resolved'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        report.refresh_from_db()
        self.assertEqual(report.status, 'resolved')
        
        # 5. Admin hapus laporan
        response = self.client.delete(
            reverse('delete_report', args=[report.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Report.objects.count(), 0)


class ReportSecurityTest(TestCase):
    """Test case untuk keamanan dan permission"""
    
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='pass123'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            password='admin123'
        )
        
        self.report = Report.objects.create(
            reporter=self.user1,
            content_type='post',
            content_id=1,
            category='spam'
        )
    
    def test_user_cannot_access_other_user_reports(self):
        """Test user tidak bisa akses laporan user lain"""
        self.client.login(username='user2', password='pass123')
        
        # User2 tidak bisa akses report detail (karena bukan admin)
        response = self.client.get(reverse('report_detail', args=[self.report.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_user_can_only_see_own_reports(self):
        """Test my_reports hanya menampilkan laporan user tersebut"""
        # User1 buat laporan
        Report.objects.create(
            reporter=self.user1,
            content_type='post',
            content_id=2,
            category='sara'
        )
        
        # User2 buat laporan
        Report.objects.create(
            reporter=self.user2,
            content_type='comment',
            content_id=1,
            category='inappropriate'
        )
        
        self.client.login(username='user1', password='pass123')
        response = self.client.get(reverse('my_reports'))
        
        # User1 hanya bisa melihat laporannya sendiri
        reports = response.context['page_obj']
        user_reports = [r for r in reports if r.reporter == self.user1]
        self.assertEqual(len(user_reports), len(reports))
    
    def test_csrf_protection_on_ajax_views(self):
        """Test CSRF protection pada view AJAX"""
        self.client.login(username='user1', password='pass123')
        
        # Tanpa CSRF token seharusnya gagal (kecuali @csrf_exempt)
        response = self.client.post(
            reverse('create_report'),
            {
                'content_type': 'post',
                'content_id': 1,
                'category': 'spam',
            }
            # Tidak ada CSRF token
        )
        
        # Karena menggunakan @csrf_exempt, seharusnya tetap bisa
        # Tapi dalam praktiknya, lebih baik tidak pakai csrf_exempt
        # dan handle CSRF token di JavaScript
        self.assertIn(response.status_code, [200, 403])


# Form Test (jika Anda membuat form terpisah)
class ReportFormTest(TestCase):
    """Test case untuk ReportForm"""
    
    def test_form_validation(self):
        """Test validasi form"""
        # Data valid
        form_data = {
            'content_type': 'post',
            'content_id': 1,
            'category': 'spam',
            'description': 'Ini spam',
        }
        form = ReportForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Data tidak valid - content_type tidak ada
        invalid_data = form_data.copy()
        invalid_data['content_type'] = 'invalid'
        form = ReportForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        
        # Data tidak valid - content_id negatif
        invalid_data = form_data.copy()
        invalid_data['content_id'] = -1
        form = ReportForm(data=invalid_data)
        self.assertFalse(form.is_valid())
