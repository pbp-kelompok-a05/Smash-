from django import forms
from .models import Report, ReportSettings


class ReportForm(forms.ModelForm):
    """
    Form untuk membuat laporan baru oleh user.
    """
    class Meta:
        model = Report
        fields = ['category', 'description']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control',
                'id': 'report-category'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Jelaskan secara detail alasan Anda melaporkan konten ini...',
                'id': 'report-description'
            }),
        }
        labels = {
            'category': 'Kategori Pelaporan',
            'description': 'Deskripsi Tambahan (Opsional)',
        }
        help_texts = {
            'description': 'Berikan penjelasan mengapa konten ini perlu dilaporkan',
        }


class ReportAdminForm(forms.ModelForm):
    """
    Form untuk admin mengelola laporan.
    """
    class Meta:
        model = Report
        fields = ['status', 'admin_notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'admin_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Catatan internal untuk tim moderasi...'
            }),
        }
        labels = {
            'status': 'Status Laporan',
            'admin_notes': 'Catatan Admin',
        }


class ReportSettingsForm(forms.ModelForm):
    """
    Form untuk mengatur pengaturan sistem pelaporan.
    """
    class Meta:
        model = ReportSettings
        fields = [
            'auto_action_threshold',
            'notify_admin_on_report',
            'auto_hide_on_threshold',
            'keep_resolved_reports_days'
        ]
        widgets = {
            'auto_action_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10
            }),
            'keep_resolved_reports_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 365
            }),
        }
        labels = {
            'auto_action_threshold': 'Threshold Auto Action',
            'notify_admin_on_report': 'Notifikasi Admin pada Laporan Baru',
            'auto_hide_on_threshold': 'Sembunyikan Konten Otomatis pada Threshold',
            'keep_resolved_reports_days': 'Menyimpan Laporan Terselesaikan (hari)',
        }
        help_texts = {
            'auto_action_threshold': 'Jumlah laporan minimum sebelum sistem mengambil tindakan otomatis',
            'keep_resolved_reports_days': 'Laporan yang sudah resolved akan diarsipkan setelah periode ini',
        }