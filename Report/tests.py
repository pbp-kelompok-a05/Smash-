import uuid
import json
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from .models import Report, ReportSettings
from .forms import ReportForm
from Post.models import ForumPost, Category


class ReportViewTestBase(TestCase):
    """
    Base test class untuk setup data testing yang umum
    """
    
    def setUp(self):
        """
        Setup data testing yang akan digunakan di semua test cases
        """
        # Create users
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpass123'
        )
        
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()
        
        self.superuser = User.objects.create_user(
            username='superuser',
            email='super@example.com',
            password='testpass123'
        )
        self.superuser.is_superuser = True
        self.superuser.is_staff = True
        self.superuser.save()
        
        # Create test category dan post untuk reporting
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description'
        )
        
        self.forum_post = ForumPost.objects.create(
            title='Test Post',
            content='Test content for reporting',
            author=self.regular_user,
            category=self.category
        )
        
        # Create test reports
        self.pending_report = Report.objects.create(
            reporter=self.regular_user,
            content_type=ContentType.objects.get_for_model(ForumPost),
            object_id=self.forum_post.id,
            reason=Report.REASON_SPAM,
            description='This is a spam post',
            status=Report.STATUS_PENDING
        )
        
        self.resolved_report = Report.objects.create(
            reporter=self.regular_user,
            content_type=ContentType.objects.get_for_model(ForumPost),
            object_id=self.forum_post.id,
            reason=Report.REASON_HARASSMENT,
            description='This is harassment',
            status=Report.STATUS_RESOLVED,
            resolved_by=self.staff_user,
            resolved_at=timezone.now()
        )
        
        # Create client instances
        self.client = Client()
        self.factory = RequestFactory()
        
        # Report settings
        self.settings, _ = ReportSettings.objects.get_or_create(pk=1)


class ReportListViewTest(ReportViewTestBase):
    """
    Test cases untuk report_list view
    """
    
    def test_report_list_regular_user(self):
        """
        Test bahwa regular user hanya bisa melihat laporan mereka sendiri
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:report_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_list.html')
        
        # Regular user hanya harus melihat laporan mereka sendiri
        reports_in_context = response.context['reports']
        self.assertEqual(reports_in_context.count(), 2)  # Both reports belong to regular_user
        self.assertTrue(all(report.reporter == self.regular_user for report in reports_in_context))
    
    def test_report_list_staff_user(self):
        """
        Test bahwa staff user bisa melihat semua laporan
        """
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(reverse('reports:report_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_list.html')
        
        # Staff user harus melihat semua laporan
        reports_in_context = response.context['reports']
        self.assertEqual(reports_in_context.count(), 2)
    
    def test_report_list_unauthenticated(self):
        """
        Test bahwa unauthenticated user di-redirect ke login
        """
        response = self.client.get(reverse('reports:report_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_report_list_filtering(self):
        """
        Test filtering functionality pada report list
        """
        self.client.login(username='staffuser', password='testpass123')
        
        # Filter by status
        response = self.client.get(reverse('reports:report_list') + '?status=pending')
        reports_in_context = response.context['reports']
        self.assertEqual(reports_in_context.count(), 1)
        self.assertEqual(reports_in_context[0].status, Report.STATUS_PENDING)
        
        # Filter by reason
        response = self.client.get(reverse('reports:report_list') + '?reason=spam')
        reports_in_context = response.context['reports']
        self.assertEqual(reports_in_context.count(), 1)
        self.assertEqual(reports_in_context[0].reason, Report.REASON_SPAM)
    
    def test_report_list_ajax_pagination(self):
        """
        Test AJAX pagination pada report list
        """
        self.client.login(username='staffuser', password='testpass123')
        
        # Create more reports untuk test pagination
        for i in range(15):
            Report.objects.create(
                reporter=self.regular_user,
                content_type=ContentType.objects.get_for_model(ForumPost),
                object_id=self.forum_post.id,
                reason=Report.REASON_SPAM,
                description=f'Test report {i}',
                status=Report.STATUS_PENDING
            )
        
        response = self.client.get(
            reverse('reports:report_list'), 
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={'page': 1}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['reports']), 10)  # 10 items per page
        self.assertTrue(data['has_next'])
        self.assertEqual(data['next_page'], 2)


class ReportDetailViewTest(ReportViewTestBase):
    """
    Test cases untuk report_detail view
    """
    
    def test_report_detail_owner(self):
        """
        Test bahwa pemilik laporan bisa melihat detail laporan
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:report_detail', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_detail.html')
        self.assertEqual(response.context['report'], self.pending_report)
    
    def test_report_detail_staff(self):
        """
        Test bahwa staff bisa melihat detail laporan apapun
        """
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(reverse('reports:report_detail', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['report'], self.pending_report)
    
    def test_report_detail_other_user(self):
        """
        Test bahwa user lain tidak bisa melihat laporan yang bukan miliknya
        """
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.client.login(username='otheruser', password='testpass123')
        
        response = self.client.get(reverse('reports:report_detail', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 302)  # Redirect ke report list
        self.assertRedirects(response, reverse('reports:report_list'))
    
    def test_report_detail_ajax(self):
        """
        Test AJAX response untuk report detail
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(
            reverse('reports:report_detail', kwargs={'pk': self.pending_report.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['report']['id'], str(self.pending_report.id))
        self.assertEqual(data['report']['reporter'], self.regular_user.username)
    
    def test_report_detail_not_found(self):
        """
        Test response ketika laporan tidak ditemukan
        """
        self.client.login(username='regularuser', password='testpass123')
        non_existent_uuid = uuid.uuid4()
        
        response = self.client.get(reverse('reports:report_detail', kwargs={'pk': non_existent_uuid}))
        
        self.assertEqual(response.status_code, 302)  # Redirect ke report list
        self.assertRedirects(response, reverse('reports:report_list'))


class CreateReportViewTest(ReportViewTestBase):
    """
    Test cases untuk create_report view
    """
    
    def test_create_report_get_authenticated(self):
        """
        Test GET request untuk create report form (authenticated user)
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:create_report'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_form.html')
        self.assertIsInstance(response.context['form'], ReportForm)
    
    def test_create_report_get_ajax(self):
        """
        Test AJAX GET request untuk create report modal
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(
            reverse('reports:create_report'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('modal_html', data)
    
    def test_create_report_post_valid(self):
        """
        Test POST request dengan data valid untuk create report
        """
        self.client.login(username='regularuser', password='testpass123')
        
        post_data = {
            'reason': Report.REASON_SPAM,
            'description': 'This is a test report',
            'confirm_report': True
        }
        
        response = self.client.post(
            reverse('reports:create_report'),
            data=post_data,
            follow=True
        )
        
        # Check bahwa report berhasil dibuat dan di-redirect
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Report.objects.filter(description='This is a test report').exists())
    
    def test_create_report_post_ajax_valid(self):
        """
        Test AJAX POST request dengan data valid
        """
        self.client.login(username='regularuser', password='testpass123')
        
        post_data = {
            'reason': Report.REASON_SPAM,
            'description': 'This is a test report via AJAX',
            'confirm_report': True
        }
        
        response = self.client.post(
            reverse('reports:create_report'),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Report.objects.filter(description='This is a test report via AJAX').exists())
    
    def test_create_report_post_invalid(self):
        """
        Test POST request dengan data invalid
        """
        self.client.login(username='regularuser', password='testpass123')
        
        post_data = {
            'reason': '',  # Required field empty
            'description': 'Test',
            'confirm_report': True
        }
        
        response = self.client.post(reverse('reports:create_report'), data=post_data)
        
        self.assertEqual(response.status_code, 200)  # Kembali ke form dengan errors
        self.assertFalse(Report.objects.filter(description='Test').exists())
    
    def test_create_report_post_ajax_invalid(self):
        """
        Test AJAX POST request dengan data invalid
        """
        self.client.login(username='regularuser', password='testpass123')
        
        post_data = {
            'reason': '',  # Required field empty
            'description': 'Test',
            'confirm_report': True
        }
        
        response = self.client.post(
            reverse('reports:create_report'),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertIn('errors', data)
    
    def test_create_report_for_specific_content(self):
        """
        Test create report untuk konten tertentu (post/comment)
        """
        self.client.login(username='regularuser', password='testpass123')
        
        content_type = ContentType.objects.get_for_model(ForumPost)
        url = reverse('reports:create_report_for_content', kwargs={
            'content_type_id': content_type.id,
            'object_id': self.forum_post.id
        })
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Test POST untuk specific content
        post_data = {
            'reason': Report.REASON_INAPPROPRIATE,
            'description': 'Inappropriate content report',
            'confirm_report': True
        }
        
        response = self.client.post(url, data=post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify report dibuat dengan object yang benar
        report = Report.objects.get(description='Inappropriate content report')
        self.assertEqual(report.object_id, self.forum_post.id)
        self.assertEqual(report.content_type, content_type)


class UpdateReportViewTest(ReportViewTestBase):
    """
    Test cases untuk update_report view
    """
    
    def test_update_report_get_owner(self):
        """
        Test GET request oleh pemilik laporan
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:update_report', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_form.html')
        self.assertIsInstance(response.context['form'], ReportForm)
    
    def test_update_report_get_ajax(self):
        """
        Test AJAX GET request untuk update report modal
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(
            reverse('reports:update_report', kwargs={'pk': self.pending_report.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('modal_html', data)
    
    def test_update_report_post_valid(self):
        """
        Test POST request dengan data valid untuk update report
        """
        self.client.login(username='regularuser', password='testpass123')
        
        post_data = {
            'reason': Report.REASON_HARASSMENT,  # Changed reason
            'description': 'Updated description',
            'confirm_report': True
        }
        
        response = self.client.post(
            reverse('reports:update_report', kwargs={'pk': self.pending_report.id}),
            data=post_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify report di-update
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.reason, Report.REASON_HARASSMENT)
        self.assertEqual(self.pending_report.description, 'Updated description')
    
    def test_update_report_permission_denied(self):
        """
        Test bahwa user lain tidak bisa mengedit laporan
        """
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.client.login(username='otheruser', password='testpass123')
        
        response = self.client.get(reverse('reports:update_report', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 302)  # Redirect ke detail page
        self.assertRedirects(response, reverse('reports:report_detail', kwargs={'pk': self.pending_report.id}))
    
    def test_update_report_resolved_denied(self):
        """
        Test bahwa laporan yang sudah resolved tidak bisa di-edit
        """
        self.client.login(username='regularuser', password='testpass123')
        
        response = self.client.get(reverse('reports:update_report', kwargs={'pk': self.resolved_report.id}))
        
        self.assertEqual(response.status_code, 302)  # Redirect ke detail page
        self.assertRedirects(response, reverse('reports:report_detail', kwargs={'pk': self.resolved_report.id}))


class DeleteReportViewTest(ReportViewTestBase):
    """
    Test cases untuk delete_report view
    """
    
    def test_delete_report_get_owner(self):
        """
        Test GET request untuk delete confirmation oleh pemilik
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:delete_report', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_confirm_delete.html')
    
    def test_delete_report_get_ajax(self):
        """
        Test AJAX GET request untuk delete confirmation modal
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(
            reverse('reports:delete_report', kwargs={'pk': self.pending_report.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('modal_html', data)
    
    def test_delete_report_post_owner(self):
        """
        Test POST request untuk delete oleh pemilik
        """
        self.client.login(username='regularuser', password='testpass123')
        
        report_id = self.pending_report.id
        response = self.client.post(
            reverse('reports:delete_report', kwargs={'pk': report_id}),
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Report.objects.filter(id=report_id).exists())
    
    def test_delete_report_post_ajax(self):
        """
        Test AJAX POST request untuk delete
        """
        self.client.login(username='regularuser', password='testpass123')
        
        report_id = self.pending_report.id
        response = self.client.post(
            reverse('reports:delete_report', kwargs={'pk': report_id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        self.assertFalse(Report.objects.filter(id=report_id).exists())
    
    def test_delete_report_permission_denied(self):
        """
        Test bahwa user lain tidak bisa menghapus laporan
        """
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.client.login(username='otheruser', password='testpass123')
        
        response = self.client.post(reverse('reports:delete_report', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 302)  # Redirect ke detail page
        self.assertTrue(Report.objects.filter(id=self.pending_report.id).exists())


class AdminReportListViewTest(ReportViewTestBase):
    """
    Test cases untuk admin_report_list view
    """
    
    def test_admin_report_list_staff_access(self):
        """
        Test bahwa staff bisa mengakses admin report list
        """
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(reverse('reports:admin_report_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/admin_report_list.html')
        
        # Verify stats dalam context
        self.assertIn('stats', response.context)
        stats = response.context['stats']
        self.assertEqual(stats['total_reports'], 2)
    
    def test_admin_report_list_regular_user_denied(self):
        """
        Test bahwa regular user tidak bisa mengakses admin report list
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:admin_report_list'))
        
        self.assertEqual(response.status_code, 302)  # Redirect
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any('admin' in str(message).lower() for message in messages))
    
    def test_admin_report_list_filtering(self):
        """
        Test filtering pada admin report list
        """
        self.client.login(username='staffuser', password='testpass123')
        
        # Filter by status resolved
        response = self.client.get(reverse('reports:admin_report_list') + '?status=resolved')
        reports_in_context = response.context['reports']
        self.assertEqual(reports_in_context.count(), 1)
        self.assertEqual(reports_in_context[0].status, Report.STATUS_RESOLVED)


class AdminActionViewsTest(ReportViewTestBase):
    """
    Test cases untuk admin action views (mark reviewed, resolve, reject, reopen)
    """
    
    def test_mark_report_reviewed(self):
        """
        Test mark_report_reviewed action
        """
        self.client.login(username='staffuser', password='testpass123')
        
        response = self.client.post(
            reverse('reports:mark_report_reviewed', kwargs={'pk': self.pending_report.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Verify status berubah
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, Report.STATUS_UNDER_REVIEW)
    
    def test_resolve_report(self):
        """
        Test resolve_report action
        """
        self.client.login(username='staffuser', password='testpass123')
        
        post_data = {
            'action_taken': 'Content has been removed',
            'admin_notes': 'Internal note'
        }
        
        response = self.client.post(
            reverse('reports:resolve_report', kwargs={'pk': self.pending_report.id}),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Verify report resolved
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, Report.STATUS_RESOLVED)
        self.assertEqual(self.pending_report.action_taken, 'Content has been removed')
        self.assertEqual(self.pending_report.resolved_by, self.staff_user)
    
    def test_reject_report(self):
        """
        Test reject_report action
        """
        self.client.login(username='staffuser', password='testpass123')
        
        post_data = {
            'admin_notes': 'Not enough evidence'
        }
        
        response = self.client.post(
            reverse('reports:reject_report', kwargs={'pk': self.pending_report.id}),
            data=post_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Verify report rejected
        self.pending_report.refresh_from_db()
        self.assertEqual(self.pending_report.status, Report.STATUS_REJECTED)
    
    def test_reopen_report(self):
        """
        Test reopen_report action
        """
        self.client.login(username='staffuser', password='testpass123')
        
        response = self.client.post(
            reverse('reports:reopen_report', kwargs={'pk': self.resolved_report.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')
        
        # Verify report reopened
        self.resolved_report.refresh_from_db()
        self.assertEqual(self.resolved_report.status, Report.STATUS_PENDING)
        self.assertIsNone(self.resolved_report.resolved_by)
        self.assertIsNone(self.resolved_report.resolved_at)
    
    def test_admin_actions_regular_user_denied(self):
        """
        Test bahwa regular user tidak bisa melakukan admin actions
        """
        self.client.login(username='regularuser', password='testpass123')
        
        actions = [
            reverse('reports:mark_report_reviewed', kwargs={'pk': self.pending_report.id}),
            reverse('reports:resolve_report', kwargs={'pk': self.pending_report.id}),
            reverse('reports:reject_report', kwargs={'pk': self.pending_report.id}),
            reverse('reports:reopen_report', kwargs={'pk': self.resolved_report.id}),
        ]
        
        for action_url in actions:
            response = self.client.post(action_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 403)  # Forbidden


class ReportSettingsViewTest(ReportViewTestBase):
    """
    Test cases untuk report_settings view
    """
    
    def test_report_settings_staff_access(self):
        """
        Test bahwa staff bisa mengakses report settings
        """
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(reverse('reports:report_settings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reports/report_settings.html')
        self.assertIn('form', response.context)
        self.assertIn('settings', response.context)
    
    def test_report_settings_regular_user_denied(self):
        """
        Test bahwa regular user tidak bisa mengakses report settings
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:report_settings'))
        
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_report_settings_post_valid(self):
        """
        Test POST request dengan data valid untuk update settings
        """
        self.client.login(username='staffuser', password='testpass123')
        
        post_data = {
            'max_reports_per_day': 10,
            'auto_reject_after_days': 14,
            'notify_admins_on_report': True,
            'notify_reporter_on_update': False,
            'allow_anonymous_reports': True,
            'require_evidence': True
        }
        
        response = self.client.post(
            reverse('reports:report_settings'),
            data=post_data,
            follow=True
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify settings di-update
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.max_reports_per_day, 10)
        self.assertEqual(self.settings.auto_reject_after_days, 14)
        self.assertTrue(self.settings.allow_anonymous_reports)


class APIViewsTest(ReportViewTestBase):
    """
    Test cases untuk API views (JSON/XML)
    """
    
    def test_show_json_regular_user(self):
        """
        Test JSON API untuk regular user (hanya laporan sendiri)
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:show_json'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)  # Only user's own reports
    
    def test_show_json_staff_user(self):
        """
        Test JSON API untuk staff user (semua laporan)
        """
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.get(reverse('reports:show_json'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)  # All reports
    
    def test_show_xml_regular_user(self):
        """
        Test XML API untuk regular user
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:show_xml'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
    
    def test_show_json_by_id_owner(self):
        """
        Test JSON API untuk laporan spesifik oleh pemilik
        """
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('reports:show_json_by_id', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)  # Single report
    
    def test_show_json_by_id_other_user_denied(self):
        """
        Test JSON API untuk laporan spesifik oleh user lain (ditolak)
        """
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        self.client.login(username='otheruser', password='testpass123')
        
        response = self.client.get(reverse('reports:show_json_by_id', kwargs={'pk': self.pending_report.id}))
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_show_json_by_id_not_found(self):
        """
        Test JSON API untuk laporan yang tidak ditemukan
        """
        self.client.login(username='regularuser', password='testpass123')
        non_existent_uuid = uuid.uuid4()
        
        response = self.client.get(reverse('reports:show_json_by_id', kwargs={'pk': non_existent_uuid}))
        
        self.assertEqual(response.status_code, 404)


class UtilityFunctionsTest(ReportViewTestBase):
    """
    Test cases untuk utility functions dalam views
    """
    
    def test_get_ajax_response(self):
        """
        Test _get_ajax_response utility function
        """
        request = self.factory.get('/')
        request.user = self.regular_user
        
        from .views import _get_ajax_response
        
        response = _get_ajax_response(request, 'reports/report_list.html', {'test': 'data'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('modal_html', data)
    
    def test_get_report_data(self):
        """
        Test _get_report_data utility function
        """
        from .views import _get_report_data
        
        report_data = _get_report_data(self.pending_report)
        
        self.assertEqual(report_data['id'], str(self.pending_report.id))
        self.assertEqual(report_data['reporter'], self.regular_user.username)
        self.assertEqual(report_data['status_value'], Report.STATUS_PENDING)
        self.assertIn('detail_url', report_data)
    
    def test_is_staff_user(self):
        """
        Test is_staff_user utility function
        """
        from .views import is_staff_user
        
        self.assertFalse(is_staff_user(self.regular_user))
        self.assertTrue(is_staff_user(self.staff_user))
        self.assertTrue(is_staff_user(self.superuser))


class EdgeCasesTest(ReportViewTestBase):
    """
    Test cases untuk edge cases dan error scenarios
    """
    
    def test_create_report_duplicate_prevention(self):
        """
        Test pencegahan duplicate reports untuk konten yang sama
        """
        self.client.login(username='regularuser', password='testpass123')
        
        # Create first report
        post_data_1 = {
            'reason': Report.REASON_SPAM,
            'description': 'First report',
            'confirm_report': True
        }
        
        response_1 = self.client.post(reverse('reports:create_report'), data=post_data_1)
        self.assertEqual(response_1.status_code, 302)  # Redirect after success
        
        # Try to create duplicate report
        post_data_2 = {
            'reason': Report.REASON_HARASSMENT,
            'description': 'Duplicate report',
            'confirm_report': True
        }
        
        response_2 = self.client.post(reverse('reports:create_report'), data=post_data_2)
        
        # Should show error about duplicate report
        self.assertEqual(response_2.status_code, 200)  # Stay on form page
        self.assertContains(response_2, 'sudah melaporkan', status_code=200)
    
    def test_create_report_self_report_prevention(self):
        """
        Test pencegahan self-reporting
        """
        self.client.login(username='regularuser', password='testpass123')
        
        # Create a post by regular_user
        user_post = ForumPost.objects.create(
            title='My Own Post',
            content='My content',
            author=self.regular_user,
            category=self.category
        )
        
        content_type = ContentType.objects.get_for_model(ForumPost)
        url = reverse('reports:create_report_for_content', kwargs={
            'content_type_id': content_type.id,
            'object_id': user_post.id
        })
        
        post_data = {
            'reason': Report.REASON_SPAM,
            'description': 'Trying to report my own post',
            'confirm_report': True
        }
        
        response = self.client.post(url, data=post_data)
        
        # Should show error about self-reporting
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tidak dapat melaporkan', status_code=200)
    
    def test_report_with_evidence_image(self):
        """
        Test create report dengan evidence image upload
        """
        self.client.login(username='regularuser', password='testpass123')
        
        # Create a simple test image
        test_image = SimpleUploadedFile(
            "test_image.jpg",
            b"file_content",
            content_type="image/jpeg"
        )
        
        post_data = {
            'reason': Report.REASON_SARA,
            'description': 'Report with evidence image',
            'evidence_image': test_image,
            'confirm_report': True
        }
        
        response = self.client.post(reverse('reports:create_report'), data=post_data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Verify report created with image
        report = Report.objects.get(description='Report with evidence image')
        self.assertIsNotNone(report.evidence_image)
    
    def test_report_sara_validation(self):
        """
        Test validasi khusus untuk laporan SARA
        """
        self.client.login(username='regularuser', password='testpass123')
        
        # Test dengan description terlalu pendek untuk SARA
        post_data = {
            'reason': Report.REASON_SARA,
            'description': 'Short',  # Too short for SARA
            'confirm_report': True
        }
        
        response = self.client.post(reverse('reports:create_report'), data=post_data)
        
        self.assertEqual(response.status_code, 200)  # Stay on form
        self.assertContains(response, 'SARA', status_code=200)  # Error message about SARA


# Run tests dengan command: python manage.py test reports.tests