from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
import json
from .models import Report
from .forms import ReportForm

class ReportViewsTestCase(TestCase):
    def setUp(self):
        """Setup data untuk testing"""
        self.client = Client()
        
        # Buat user untuk testing
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
            email='test@example.com'
        )
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpassword123',
            email='admin@example.com'
        )
        
        # Buat report untuk testing
        self.report = Report.objects.create(
            title='Test Report',
            description='This is a test report description',
            location='Test Location',
            incident_type='violence',
            severity='medium',
            user=self.user,
            created_at=timezone.now()
        )
        
        self.report_data = {
            'title': 'New Test Report',
            'description': 'New test report description',
            'location': 'New Test Location',
            'incident_type': 'harassment',
            'severity': 'high'
        }

    def test_report_list_authenticated(self):
        """Test report_list view dengan user terautentikasi"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('report_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report_list.html')
        self.assertContains(response, 'Test Report')

    def test_report_list_unauthenticated(self):
        """Test report_list view tanpa autentikasi - harus redirect ke login"""
        response = self.client.get(reverse('report_list'))
        # Biasanya redirect ke login page, status code 302
        self.assertEqual(response.status_code, 302)

    def test_report_detail_authenticated(self):
        """Test report_detail view dengan user terautentikasi"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('report_detail', args=[self.report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report_detail.html')
        self.assertContains(response, self.report.title)

    def test_report_detail_unauthenticated(self):
        """Test report_detail view tanpa autentikasi"""
        response = self.client.get(reverse('report_detail', args=[self.report.id]))
        self.assertEqual(response.status_code, 302)  # Redirect ke login

    def test_report_detail_not_found(self):
        """Test report_detail dengan ID yang tidak ada"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('report_detail', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_create_report_get_authenticated(self):
        """Test GET request untuk create_report dengan user terautentikasi"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.get(reverse('create_report'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'create_report.html')
        self.assertIsInstance(response.context['form'], ReportForm)

    def test_create_report_post_valid(self):
        """Test POST request untuk create_report dengan data valid"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(reverse('create_report'), data=self.report_data)
        
        # Cek apakah redirect ke report_list setelah sukses
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('report_list'))
        
        # Cek apakah report berhasil dibuat
        self.assertTrue(Report.objects.filter(title='New Test Report').exists())
        
        # Cek apakah user terassign dengan benar
        new_report = Report.objects.get(title='New Test Report')
        self.assertEqual(new_report.user, self.user)

    def test_create_report_post_invalid(self):
        """Test POST request untuk create_report dengan data invalid"""
        self.client.login(username='testuser', password='testpassword123')
        invalid_data = {
            'title': '',  # Title kosong - harusnya invalid
            'description': 'Test description',
            'location': 'Test Location',
            'incident_type': 'harassment',
            'severity': 'high'
        }
        response = self.client.post(reverse('create_report'), data=invalid_data)
        
        # Harus tetap di page yang sama (status 200) dan form errors
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'title', 'This field is required.')

    def test_create_report_ajax_valid(self):
        """Test create_report dengan AJAX request dan data valid"""
        self.client.login(username='testuser', password='testpassword123')
        response = self.client.post(
            reverse('create_report'),
            data=self.report_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['message'], 'Laporan berhasil dibuat')
        self.assertIn('report_id', response_data)

    def test_create_report_ajax_invalid(self):
        """Test create_report dengan AJAX request dan data invalid"""
        self.client.login(username='testuser', password='testpassword123')
        invalid_data = {
            'title': '',  # Invalid: title kosong
            'description': 'Test description',
            'location': 'Test Location',
            'incident_type': 'harassment',
            'severity': 'high'
        }
        response = self.client.post(
            reverse('create_report'),
            data=invalid_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        self.assertIn('title', response_data['errors'])

    def test_show_json(self):
        """Test show_json view"""
        response = self.client.get(reverse('show_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse JSON response
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 1)  # Harusnya ada 1 report di setup
        self.assertEqual(json_data[0]['fields']['title'], 'Test Report')

    def test_show_xml(self):
        """Test show_xml view"""
        response = self.client.get(reverse('show_xml'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertIn(b'Test Report', response.content)

    def test_show_json_by_id(self):
        """Test show_json_by_id dengan ID yang valid"""
        response = self.client.get(reverse('show_json_by_id', args=[self.report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        json_data = json.loads(response.content)
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]['fields']['title'], 'Test Report')

    def test_show_json_by_id_not_found(self):
        """Test show_json_by_id dengan ID yang tidak ada"""
        response = self.client.get(reverse('show_json_by_id', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_show_xml_by_id(self):
        """Test show_xml_by_id dengan ID yang valid"""
        response = self.client.get(reverse('show_xml_by_id', args=[self.report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')
        self.assertIn(b'Test Report', response.content)

    def test_show_xml_by_id_not_found(self):
        """Test show_xml_by_id dengan ID yang tidak ada"""
        response = self.client.get(reverse('show_xml_by_id', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_report_ordering(self):
        """Test urutan report (harusnya berdasarkan created_at descending)"""
        # Buat report kedua
        report2 = Report.objects.create(
            title='Second Report',
            description='Second report description',
            location='Second Location',
            incident_type='violence',
            severity='low',
            user=self.user
        )
        
        response = self.client.get(reverse('show_json'))
        json_data = json.loads(response.content)
        
        # Report terbaru harus ada di index 0
        self.assertEqual(json_data[0]['fields']['title'], 'Second Report')

class ReportModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='modeluser',
            password='testpass123'
        )
    
    def test_report_creation(self):
        """Test pembuatan model Report"""
        report = Report.objects.create(
            title='Model Test Report',
            description='Model test description',
            location='Model Test Location',
            incident_type='harassment',
            severity='high',
            user=self.user
        )
        
        self.assertEqual(report.title, 'Model Test Report')
        self.assertEqual(report.user, self.user)
        self.assertTrue(isinstance(report.created_at, type(timezone.now())))
    
    def test_report_string_representation(self):
        """Test string representation dari model Report"""
        report = Report.objects.create(
            title='String Test Report',
            description='Test description',
            location='Test Location',
            incident_type='violence',
            severity='medium',
            user=self.user
        )
        
        self.assertEqual(str(report), 'String Test Report')

class ReportFormTestCase(TestCase):
    def test_valid_form(self):
        """Test ReportForm dengan data valid"""
        form_data = {
            'title': 'Form Test Report',
            'description': 'Form test description',
            'location': 'Form Test Location',
            'incident_type': 'harassment',
            'severity': 'medium'
        }
        form = ReportForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_title(self):
        """Test ReportForm dengan title kosong"""
        form_data = {
            'title': '',  # Title required
            'description': 'Form test description',
            'location': 'Form Test Location',
            'incident_type': 'harassment',
            'severity': 'medium'
        }
        form = ReportForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
    def test_invalid_form_missing_description(self):
        """Test ReportForm dengan description kosong"""
        form_data = {
            'title': 'Test Title',
            'description': '',  # Description required
            'location': 'Form Test Location',
            'incident_type': 'harassment',
            'severity': 'medium'
        }
        form = ReportForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('description', form.errors)

class AuthenticationTestCase(TestCase):
    def test_login_required_views(self):
        """Test bahwa views tertentu membutuhkan login"""
        views_to_test = [
            reverse('report_list'),
            reverse('create_report'),
        ]
        
        for view_url in views_to_test:
            response = self.client.get(view_url)
            self.assertEqual(response.status_code, 302)  # Redirect ke login

# Test tambahan untuk coverage yang lebih baik
class EdgeCasesTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='edgeuser',
            password='edgepass123'
        )
        self.client.login(username='edgeuser', password='edgepass123')
    
    def test_create_report_empty_post(self):
        """Test create_report dengan POST data kosong"""
        response = self.client.post(reverse('create_report'), {})
        self.assertEqual(response.status_code, 200)  # Tetap di page yang sama
        self.assertFormError(response, 'form', 'title', 'This field is required.')
        self.assertFormError(response, 'form', 'description', 'This field is required.')