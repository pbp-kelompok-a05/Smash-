from django import forms
from django.core.exceptions import ValidationError
from .models import Report

class ReportForm(forms.ModelForm):
    """
    Form untuk membuat laporan baru oleh user
    """
    class Meta:
        model = Report
        fields = ['content_type', 'content_id', 'category', 'description']
        widgets = {
            'content_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'content_type',
                'required': True,
            }),
            'content_id': forms.NumberInput(attrs={
                'class': 'form-control',
                'id': 'content_id',
                'required': True,
                'min': 1,
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'category',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'id': 'description',
                'rows': 4,
                'placeholder': 'Jelaskan alasan pelaporan secara detail...',
                'maxlength': 1000,
            }),
        }
        labels = {
            'content_type': 'Jenis Konten',
            'content_id': 'ID Konten',
            'category': 'Kategori Pelanggaran',
            'description': 'Deskripsi Laporan',
        }
        help_texts = {
            'content_id': 'Masukkan ID dari post atau komentar yang ingin dilaporkan',
            'description': 'Wajib diisi untuk kategori SARA dan Konten Tidak Senonoh',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize choice labels untuk lebih user-friendly
        self.fields['content_type'].choices = [
            ('post', '📝 Post'),
            ('comment', '💬 Komentar'),
        ]
        
        self.fields['category'].choices = [
            ('sara', '🚫 SARA (Suku, Agama, Ras, Antar-golongan)'),
            ('spam', '📢 Spam atau Iklan Tidak Sah'),
            ('inappropriate', '🔞 Konten Tidak Senonoh'),
            ('other', '❓ Lainnya'),
        ]

    def clean_content_id(self):
        """
        Validasi bahwa content_id harus positif
        """
        content_id = self.cleaned_data.get('content_id')
        if content_id <= 0:
            raise ValidationError('ID konten harus berupa angka positif')
        return content_id

    def clean_description(self):
        """
        Validasi deskripsi untuk kategori tertentu
        """
        description = self.cleaned_data.get('description', '').strip()
        category = self.cleaned_data.get('category')
        
        # Untuk kategori SARA dan inappropriate, deskripsi wajib diisi
        if category in ['sara', 'inappropriate'] and not description:
            raise ValidationError(
                f'Deskripsi wajib diisi untuk kategori {self.get_category_display(category)}'
            )
        
        # Batasi panjang deskripsi
        if len(description) > 1000:
            raise ValidationError('Deskripsi maksimal 1000 karakter')
            
        return description

    def get_category_display(self, category_code):
        """
        Helper method untuk mendapatkan display name dari category code
        """
        category_dict = dict(self.fields['category'].choices)
        return category_dict.get(category_code, category_code)


class ReportUpdateForm(forms.ModelForm):
    """
    Form untuk mengupdate status laporan oleh admin
    """
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Catatan internal untuk tim moderator...',
            'maxlength': 500,
        }),
        label='Catatan Admin',
        help_text='Catatan internal yang tidak dilihat oleh user yang melaporkan'
    )

    class Meta:
        model = Report
        fields = ['status', 'handled_by']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
                'id': 'status-update',
            }),
            'handled_by': forms.HiddenInput(),  # Diset otomatis oleh view
        }
        labels = {
            'status': 'Status Laporan',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom status choices dengan label yang lebih informatif
        self.fields['status'].choices = [
            ('pending', '⏳ Menunggu Review'),
            ('under_review', '🔍 Sedang Ditinjau'),
            ('resolved', '✅ Selesai - Konten Ditindak'),
            ('dismissed', '❌ Ditolak - Laporan Tidak Valid'),
        ]

    def clean_status(self):
        """
        Validasi perubahan status
        """
        status = self.cleaned_data.get('status')
        instance = self.instance
        
        # Jika laporan sudah resolved/dismissed, tidak bisa kembali ke pending
        if instance.pk and instance.status in ['resolved', 'dismissed'] and status == 'pending':
            raise ValidationError(
                'Laporan yang sudah selesai tidak bisa dikembalikan ke status menunggu'
            )
            
        return status


class ReportFilterForm(forms.Form):
    """
    Form untuk filtering laporan di admin dashboard
    """
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Semua Status')] + list(Report.STATUS_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()',
        }),
        label='Filter Status'
    )
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'Semua Kategori')] + list(Report.CATEGORY_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()',
        }),
        label='Filter Kategori'
    )
    
    date_range = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Semua Waktu'),
            ('today', 'Hari Ini'),
            ('week', '7 Hari Terakhir'),
            ('month', '30 Hari Terakhir'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'onchange': 'this.form.submit()',
        }),
        label='Rentang Waktu'
    )


class ReportSearchForm(forms.Form):
    """
    Form untuk pencarian laporan
    """
    SEARCH_CHOICES = [
        ('reporter', 'Pelapor'),
        ('content_id', 'ID Konten'),
        ('description', 'Deskripsi'),
    ]
    
    search_type = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        initial='content_id',
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Cari Berdasarkan'
    )
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan kata kunci pencarian...',
        }),
        label='Kata Kunci'
    )
    
    def clean_search_query(self):
        """
        Validasi query pencarian
        """
        query = self.cleaned_data.get('search_query', '').strip()
        if query and len(query) < 2:
            raise ValidationError('Kata kunci pencarian minimal 2 karakter')
        return query


class BulkReportActionForm(forms.Form):
    """
    Form untuk aksi bulk pada laporan (admin)
    """
    ACTION_CHOICES = [
        ('', '--- Pilih Aksi ---'),
        ('mark_under_review', 'Tandai Sedang Ditinjau'),
        ('mark_resolved', 'Tandai Selesai'),
        ('mark_dismissed', 'Tandai Ditolak'),
        ('delete', 'Hapus Laporan Terpilih'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        label='Aksi Massal'
    )
    
    reports = forms.ModelMultipleChoiceField(
        queryset=Report.objects.all(),
        widget=forms.MultipleHiddenInput(),
        required=True,
        label='Laporan Terpilih'
    )
    
    def clean(self):
        """
        Validasi aksi bulk
        """
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        reports = cleaned_data.get('reports')
        
        if action == 'delete' and reports and reports.count() > 10:
            raise ValidationError(
                'Maksimal 10 laporan dapat dihapus sekaligus untuk keamanan'
            )
            
        return cleaned_data


# Form untuk AJAX requests
class ReportAJAXForm(forms.ModelForm):
    """
    Form khusus untuk request AJAX (minimal validation)
    """
    class Meta:
        model = Report
        fields = ['content_type', 'content_id', 'category', 'description']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove labels and help texts for AJAX to reduce payload
        for field in self.fields:
            self.fields[field].label = ''
            self.fields[field].help_text = ''


class ReportStatusAJAXForm(forms.Form):
    """
    Form untuk update status via AJAX
    """
    status = forms.ChoiceField(
        choices=Report.STATUS_CHOICES,
        required=True
    )
    
    def clean_status(self):
        status = self.cleaned_data.get('status')
        if status not in dict(Report.STATUS_CHOICES):
            raise ValidationError('Status tidak valid')
        return status