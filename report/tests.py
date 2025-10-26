# report/tests.py
import json
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Report
from post.models import Post
from comment.models import Comment

User = get_user_model()


class ReportModelTest(TestCase):
    """
    Test suite untuk model Report.
    Meliputi: pembuatan model, validasi, methods, dan constraints.
    """
    
    def setUp(self):
        """Setup data test untuk model Report"""
        # Buat users
        self.reporter = User.objects.create_user(
            username='reporter_user',
            email='reporter@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='testpass123',
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        
        # Buat post untuk testing
        self.post = Post.objects.create(
            title='Test Post',
            content='This is a test post content',
            user=self.regular_user
        )
        
        # Buat comment untuk testing
        self.comment = Comment.objects.create(
            content='This is a test comment',
            user=self.regular_user,
            post=self.post
        )
    
    def test_create_report_with_post(self):
        """Test membuat laporan dengan post"""
        report = Report.objects.create(
            reporter=self.reporter,
            post=self.post,
            category='SPAM',
            description='This is spam content'
        )
        
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.post, self.post)
        self.assertIsNone(report.comment)
        self.assertEqual(report.category, 'SPAM')
        self.assertEqual(report.description, 'This is spam content')
        self.assertEqual(report.status, 'PENDING')
        self.assertIsNotNone(report.created_at)
        self.assertIsNone(report.reviewed_at)
        self.assertIsNone(report.reviewed_by)
    
    def test_create_report_with_comment(self):
        """Test membuat laporan dengan comment"""
        report = Report.objects.create(
            reporter=self.reporter,
            comment=self.comment,
            category='NSFW',
            description='Inappropriate content'
        )
        
        self.assertEqual(report.reporter, self.reporter)
        self.assertEqual(report.comment, self.comment)
        self.assertIsNone(report.post)
        self.assertEqual(report.category, 'NSFW')
        self.assertEqual(report.status, 'PENDING')
    
    def test_report_string_representation(self):
        """Test string representation model Report"""
        report = Report.objects.create(
            reporter=self.reporter,
            post=self.post,
            category='SARA'
        )
        
        expected_str = f"Laporan SARA oleh {self.reporter.username}"
        self.assertEqual(str(report), expected_str)
    
    def test_report_clean_method_valid(self):
        """Test clean method dengan data valid"""
        report = Report(
            reporter=self.reporter,
            post=self.post,
            category='SPAM'
        )
        
        # Tidak seharusnya raise exception
        try:
            report.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")
    
    def test_report_clean_method_no_content(self):
        """Test clean method tanpa post atau comment"""
        report = Report(
            reporter=self.reporter,
            category='SPAM'
        )
        
        with self.assertRaises(ValidationError):
            report.clean()
    
    def test_report_clean_method_both_content(self):
        """Test clean method dengan post dan comment"""
        report = Report(
            reporter=self.reporter,
            post=self.post,
            comment=self.comment,
            category='SPAM'
        )
        
        with self.assertRaises(ValidationError):
            report.clean()
    
    def test_report_save_method_reviewed_status(self):
        """Test save method saat status berubah ke REVIEWED"""
        report = Report.objects.create(
            reporter=self.reporter,
            post=self.post,
            category='SPAM',
            status='PENDING'
        )
        
        # Ubah status ke REVIEWED
        report.status = 'REVIEWED'
        report.reviewed_by = self.admin_user
        report.save()
        
        self.assertIsNotNone(report.reviewed_at)
        self.assertEqual(report.reviewed_by, self.admin_user)
    
    def test_report_ordering(self):
        """Test ordering model Report"""
        # Buat beberapa report dengan timestamp berbeda
        report1 = Report.objects.create(
            reporter=self.reporter,
            post=self.post,
            category='SPAM'
        )
        
        report2 = Report.objects.create(
            reporter=self.reporter,
            comment=self.comment,
            category='NSFW'
        )
        
        reports = Report.objects.all()
        self.assertEqual(reports[0], report2)  # Yang terbaru pertama
        self.assertEqual(reports[1], report1)
    
    def test_report_category_choices(self):
        """Test pilihan kategori yang tersedia"""
        report = Report()
        categories = dict(report.REPORT_CATEGORIES)
        
        self.assertEqual(categories['SARA'], 'Konten SARA')
        self.assertEqual(categories['SPAM'], 'Spam')
        self.assertEqual(categories['NSFW'], 'Konten Tidak Senonoh')
        self.assertEqual(categories['OTHER'], 'Lainnya')
    
    def test_report_status_choices(self):
        """Test pilihan status yang tersedia"""
        report = Report()
        statuses = dict(report.STATUS_CHOICES)
        
        self.assertEqual(statuses['PENDING'], 'Menunggu Review')
        self.assertEqual(statuses['REVIEWED'], 'Ditinjau')
        self.assertEqual(statuses['RESOLVED'], 'Selesai')
    
    def test_report_permissions(self):
        """Test custom permissions"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        content_type = ContentType.objects.get_for_model(Report)
        permission = Permission.objects.get(
            codename='manage_all_reports',
            content_type=content_type,
        )
        
        self.assertEqual(permission.name, 'Can manage all reports')


class ReportAPIViewTest(TestCase):
    """
    Test suite untuk ReportAPIView.
    Meliputi: GET, POST, PUT, DELETE operations dengan berbagai skenario.
    """
    
    def setUp(self):
        """Setup data test untuk ReportAPIView"""
        self.client = Client()
        
        # Buat users
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='testpass123',
            is_superuser=True
        )
        self.other_user = User.objects.create_user(
            username='other_user',
            email='other@example.com',
            password='testpass123'
        )
        
        # Buat post dan comment
        self.post = Post.objects.create(
            title='Test Post for Report',
            content='This is a test post content',
            user=self.other_user
        )
        
        self.comment = Comment.objects.create(
            content='This is a test comment for report',
            user=self.other_user,
            post=self.post
        )
        
        # Buat beberapa reports
        self.report1 = Report.objects.create(
            reporter=self.regular_user,
            post=self.post,
            category='SPAM',
            description='Spam content'
        )
        
        self.report2 = Report.objects.create(
            reporter=self.regular_user,
            comment=self.comment,
            category='NSFW',
            status='REVIEWED',
            reviewed_by=self.admin_user,
            reviewed_at=timezone.now()
        )
        
        # URLs
        self.report_list_url = reverse('report_api')
        self.report_detail_url = lambda id: reverse('report_api_detail', args=[id])
        self.report_stats_url = reverse('report_stats')
    
    def test_get_reports_unauthenticated(self):
        """Test GET reports tanpa autentikasi"""
        response = self.client.get(self.report_list_url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_get_reports_regular_user(self):
        """Test GET reports dengan user biasa (bukan admin)"""
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(self.report_list_url)
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_get_reports_admin_user(self):
        """Test GET reports dengan admin user"""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(self.report_list_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['reports']), 2)
    
    def test_get_single_report_admin(self):
        """Test GET single report dengan admin user"""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(self.report_detail_url(self.report1.id))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['report']['id'], self.report1.id)
        self.assertEqual(data['report']['category'], 'SPAM')
    
    def test_get_single_report_not_found(self):
        """Test GET single report dengan ID tidak ditemukan"""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(self.report_detail_url(999))
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_get_reports_with_filters(self):
        """Test GET reports dengan filter status dan kategori"""
        self.client.login(username='admin_user', password='testpass123')
        
        # Filter by status
        response = self.client.get(f"{self.report_list_url}?status=PENDING")
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['status'], 'Menunggu Review')
        
        # Filter by category
        response = self.client.get(f"{self.report_list_url}?category=NSFW")
        data = response.json()
        self.assertEqual(len(data['reports']), 1)
        self.assertTrue('Konten Tidak Senonoh' in data['reports'][0]['category'])
    
    def test_get_reports_pagination(self):
        """Test GET reports dengan pagination"""
        # Buat lebih banyak reports untuk testing pagination
        for i in range(25):
            Report.objects.create(
                reporter=self.regular_user,
                post=self.post,
                category='SPAM',
                description=f'Spam report {i}'
            )
        
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(f"{self.report_list_url}?page=2&per_page=10")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['pagination']['page'], 2)
        self.assertEqual(data['pagination']['per_page'], 10)
        self.assertEqual(len(data['reports']), 10)
    
    def test_create_report_unauthenticated(self):
        """Test POST create report tanpa autentikasi"""
        report_data = {
            'category': 'SPAM',
            'post_id': self.post.id
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_create_report_with_post(self):
        """Test POST create report untuk post"""
        self.client.login(username='regular_user', password='testpass123')
        
        report_data = {
            'category': 'SPAM',
            'post_id': self.post.id,
            'description': 'This is spam content'
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['message'], 'Laporan berhasil dikirim')
        
        # Verifikasi report dibuat di database
        report = Report.objects.get(id=data['report_id'])
        self.assertEqual(report.post, self.post)
        self.assertEqual(report.category, 'SPAM')
        self.assertEqual(report.reporter, self.regular_user)
    
    def test_create_report_with_comment(self):
        """Test POST create report untuk comment"""
        self.client.login(username='regular_user', password='testpass123')
        
        report_data = {
            'category': 'NSFW',
            'comment_id': self.comment.id,
            'description': 'Inappropriate comment'
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Verifikasi report dibuat
        report = Report.objects.get(id=data['report_id'])
        self.assertEqual(report.comment, self.comment)
        self.assertEqual(report.category, 'NSFW')
    
    def test_create_report_missing_category(self):
        """Test POST create report tanpa kategori"""
        self.client.login(username='regular_user', password='testpass123')
        
        report_data = {
            'post_id': self.post.id
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_create_report_missing_content(self):
        """Test POST create report tanpa post_id atau comment_id"""
        self.client.login(username='regular_user', password='testpass123')
        
        report_data = {
            'category': 'SPAM'
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_create_report_invalid_post_id(self):
        """Test POST create report dengan post_id tidak valid"""
        self.client.login(username='regular_user', password='testpass123')
        
        report_data = {
            'category': 'SPAM',
            'post_id': 999  # ID tidak ada
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_create_report_invalid_json(self):
        """Test POST create report dengan JSON tidak valid"""
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.post(
            self.report_list_url,
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_update_report_status_unauthenticated(self):
        """Test PUT update report status tanpa autentikasi"""
        update_data = {
            'status': 'REVIEWED'
        }
        
        response = self.client.put(
            self.report_detail_url(self.report1.id),
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_update_report_status_regular_user(self):
        """Test PUT update report status dengan user biasa"""
        self.client.login(username='regular_user', password='testpass123')
        
        update_data = {
            'status': 'REVIEWED'
        }
        
        response = self.client.put(
            self.report_detail_url(self.report1.id),
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_update_report_status_admin(self):
        """Test PUT update report status dengan admin user"""
        self.client.login(username='admin_user', password='testpass123')
        
        update_data = {
            'status': 'REVIEWED'
        }
        
        response = self.client.put(
            self.report_detail_url(self.report1.id),
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['new_status'], 'Ditinjau')
        
        # Verifikasi update di database
        self.report1.refresh_from_db()
        self.assertEqual(self.report1.status, 'REVIEWED')
        self.assertIsNotNone(self.report1.reviewed_at)
        self.assertEqual(self.report1.reviewed_by, self.admin_user)
    
    def test_update_report_status_resolved(self):
        """Test PUT update report status ke RESOLVED"""
        self.client.login(username='admin_user', password='testpass123')
        
        update_data = {
            'status': 'RESOLVED'
        }
        
        response = self.client.put(
            self.report_detail_url(self.report1.id),
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi update di database
        self.report1.refresh_from_db()
        self.assertEqual(self.report1.status, 'RESOLVED')
    
    def test_delete_report_unauthenticated(self):
        """Test DELETE report tanpa autentikasi"""
        response = self.client.delete(self.report_detail_url(self.report1.id))
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_delete_report_regular_user(self):
        """Test DELETE report dengan user biasa"""
        self.client.login(username='regular_user', password='testpass123')
        
        response = self.client.delete(self.report_detail_url(self.report1.id))
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_delete_report_admin(self):
        """Test DELETE report dengan admin user"""
        self.client.login(username='admin_user', password='testpass123')
        
        report_id = self.report1.id
        response = self.client.delete(self.report_detail_url(report_id))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verifikasi report dihapus dari database
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=report_id)
    
    def test_delete_report_not_found(self):
        """Test DELETE report dengan ID tidak ditemukan"""
        self.client.login(username='admin_user', password='testpass123')
        
        response = self.client.delete(self.report_detail_url(999))
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')


class ReportStatsViewTest(TestCase):
    """
    Test suite untuk ReportStatsView.
    Meliputi: pengambilan statistik dengan berbagai kondisi.
    """
    
    def setUp(self):
        """Setup data test untuk ReportStatsView"""
        self.client = Client()
        
        # Buat users
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin_user',
            email='admin@example.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Buat post untuk testing
        self.post = Post.objects.create(
            title='Test Post for Stats',
            content='This is a test post content',
            user=self.regular_user
        )
        
        # Buat reports dengan berbagai status dan kategori
        Report.objects.create(
            reporter=self.regular_user,
            post=self.post,
            category='SPAM',
            status='PENDING'
        )
        Report.objects.create(
            reporter=self.regular_user,
            post=self.post,
            category='SPAM',
            status='REVIEWED',
            reviewed_by=self.admin_user,
            reviewed_at=timezone.now()
        )
        Report.objects.create(
            reporter=self.regular_user,
            post=self.post,
            category='NSFW',
            status='PENDING'
        )
        Report.objects.create(
            reporter=self.regular_user,
            post=self.post,
            category='SARA',
            status='RESOLVED'
        )
        Report.objects.create(
            reporter=self.regular_user,
            post=self.post,
            category='OTHER',
            status='REVIEWED',
            reviewed_by=self.admin_user,
            reviewed_at=timezone.now()
        )
        
        self.report_stats_url = reverse('report_stats')
    
    def test_get_stats_unauthenticated(self):
        """Test GET stats tanpa autentikasi"""
        response = self.client.get(self.report_stats_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_get_stats_regular_user(self):
        """Test GET stats dengan user biasa"""
        self.client.login(username='regular_user', password='testpass123')
        response = self.client.get(self.report_stats_url)
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_get_stats_admin_user(self):
        """Test GET stats dengan admin user"""
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(self.report_stats_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Verifikasi statistics
        stats = data['statistics']
        self.assertEqual(stats['total'], 5)
        self.assertEqual(stats['pending'], 2)
        self.assertEqual(stats['reviewed'], 2)
        self.assertEqual(stats['resolved'], 1)
        
        # Verifikasi category statistics
        categories = stats['categories']
        self.assertEqual(categories['SPAM']['count'], 2)
        self.assertEqual(categories['NSFW']['count'], 1)
        self.assertEqual(categories['SARA']['count'], 1)
        self.assertEqual(categories['OTHER']['count'], 1)
        
        # Verifikasi recent activity
        self.assertEqual(len(data['recent_activity']), 5)
    
    def test_get_stats_empty_reports(self):
        """Test GET stats ketika tidak ada reports"""
        # Hapus semua reports
        Report.objects.all().delete()
        
        self.client.login(username='admin_user', password='testpass123')
        response = self.client.get(self.report_stats_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        stats = data['statistics']
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['reviewed'], 0)
        self.assertEqual(stats['resolved'], 0)
        
        # Verifikasi semua kategori memiliki count 0
        for category in stats['categories'].values():
            self.assertEqual(category['count'], 0)


class ReportIntegrationTest(TestCase):
    """
    Test integrasi untuk modul Report.
    Meliputi: alur lengkap dari pembuatan hingga penyelesaian laporan.
    """
    
    def setUp(self):
        """Setup data test untuk integration test"""
        self.client = Client()
        
        # Buat users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_superuser=True
        )
        
        # Buat post dan comment
        self.post = Post.objects.create(
            title='Integration Test Post',
            content='This is a post for integration testing',
            user=self.user2
        )
        
        self.comment = Comment.objects.create(
            content='This is a comment for integration testing',
            user=self.user2,
            post=self.post
        )
        
        self.report_list_url = reverse('report_api')
        self.report_detail_url = lambda id: reverse('report_api_detail', args=[id])
        self.report_stats_url = reverse('report_stats')
    
    def test_complete_report_workflow(self):
        """
        Test alur lengkap laporan:
        1. User membuat laporan
        2. Admin melihat daftar laporan
        3. Admin mengupdate status laporan
        4. Admin menghapus laporan
        5. Verifikasi statistik
        """
        
        # 1. User membuat laporan untuk post
        self.client.login(username='user1', password='testpass123')
        
        report_data = {
            'category': 'SPAM',
            'post_id': self.post.id,
            'description': 'This post appears to be spam'
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        report_id = response.json()['report_id']
        
        # 2. Admin melihat daftar laporan
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(self.report_list_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['reports']), 1)
        self.assertEqual(data['reports'][0]['status'], 'Menunggu Review')
        
        # 3. Admin mengupdate status laporan
        update_data = {
            'status': 'REVIEWED'
        }
        
        response = self.client.put(
            self.report_detail_url(report_id),
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi update di database
        report = Report.objects.get(id=report_id)
        self.assertEqual(report.status, 'REVIEWED')
        self.assertIsNotNone(report.reviewed_at)
        self.assertEqual(report.reviewed_by, self.admin)
        
        # 4. Admin menghapus laporan
        response = self.client.delete(self.report_detail_url(report_id))
        self.assertEqual(response.status_code, 200)
        
        # Verifikasi laporan dihapus
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=report_id)
        
        # 5. Verifikasi statistik menunjukkan 0 laporan
        response = self.client.get(self.report_stats_url)
        self.assertEqual(response.status_code, 200)
        
        stats = response.json()['statistics']
        self.assertEqual(stats['total'], 0)
    
    def test_multiple_reports_statistics(self):
        """Test statistik dengan multiple reports"""
        # Buat beberapa reports dengan status berbeda
        reports_data = [
            {'category': 'SPAM', 'status': 'PENDING'},
            {'category': 'SPAM', 'status': 'REVIEWED'},
            {'category': 'NSFW', 'status': 'PENDING'},
            {'category': 'SARA', 'status': 'RESOLVED'},
            {'category': 'OTHER', 'status': 'REVIEWED'},
        ]
        
        for data in reports_data:
            Report.objects.create(
                reporter=self.user1,
                post=self.post,
                category=data['category'],
                status=data['status']
            )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(self.report_stats_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        stats = data['statistics']
        self.assertEqual(stats['total'], 5)
        self.assertEqual(stats['pending'], 2)
        self.assertEqual(stats['reviewed'], 2)
        self.assertEqual(stats['resolved'], 1)
        
        # Verifikasi category counts
        categories = stats['categories']
        self.assertEqual(categories['SPAM']['count'], 2)
        self.assertEqual(categories['NSFW']['count'], 1)
        self.assertEqual(categories['SARA']['count'], 1)
        self.assertEqual(categories['OTHER']['count'], 1)


class ReportEdgeCasesTest(TestCase):
    """
    Test untuk edge cases dan skenario khusus.
    """
    
    def setUp(self):
        """Setup data test untuk edge cases"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_superuser=True
        )
        
        self.post = Post.objects.create(
            title='Edge Case Post',
            content='Content for edge case testing',
            user=self.user
        )
        
        self.report_list_url = reverse('report_api')
    
    def test_create_report_own_content(self):
        """
        Test bahwa user tidak bisa melaporkan konten sendiri.
        Ini adalah validasi yang harus dilakukan di form level.
        """
        # User mencoba melaporkan post miliknya sendiri
        self.client.login(username='testuser', password='testpass123')
        
        own_post = Post.objects.create(
            title='My Own Post',
            content='This is my own post',
            user=self.user
        )
        
        report_data = {
            'category': 'SPAM',
            'post_id': own_post.id
        }
        
        # Catatan: Validasi ini seharusnya dilakukan di form, bukan di view
        # View saat ini tidak melakukan validasi ini
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        # Karena view tidak memeriksa kepemilikan, laporan akan dibuat
        # Ini mungkin perlu dipertimbangkan untuk improvement
        self.assertEqual(response.status_code, 201)
    
    def test_create_report_deleted_content(self):
        """Test membuat laporan untuk konten yang sudah dihapus"""
        self.client.login(username='testuser', password='testpass123')
        
        # Buat post lalu hapus
        post_to_delete = Post.objects.create(
            title='Post to Delete',
            content='This post will be deleted',
            user=self.user
        )
        post_id = post_to_delete.id
        post_to_delete.is_deleted = True
        post_to_delete.save()
        
        report_data = {
            'category': 'SPAM',
            'post_id': post_id
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        # Seharusnya gagal karena post sudah dihapus
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['status'], 'error')
    
    def test_report_with_long_description(self):
        """Test membuat laporan dengan deskripsi panjang"""
        self.client.login(username='testuser', password='testpass123')
        
        long_description = 'A' * 500  # Batas maksimal
        
        report_data = {
            'category': 'SPAM',
            'post_id': self.post.id,
            'description': long_description
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verifikasi deskripsi tersimpan dengan benar
        report_id = response.json()['report_id']
        report = Report.objects.get(id=report_id)
        self.assertEqual(len(report.description), 500)
    
    def test_report_with_empty_description(self):
        """Test membuat laporan dengan deskripsi kosong"""
        self.client.login(username='testuser', password='testpass123')
        
        report_data = {
            'category': 'SPAM',
            'post_id': self.post.id,
            'description': ''
        }
        
        response = self.client.post(
            self.report_list_url,
            data=json.dumps(report_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verifikasi deskripsi kosong tersimpan
        report_id = response.json()['report_id']
        report = Report.objects.get(id=report_id)
        self.assertEqual(report.description, '')