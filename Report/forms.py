# report/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import escape
from .models import Report
from post.models import Post
from comment.models import Comment

class ReportCreateForm(forms.ModelForm):
    """
    Form untuk membuat laporan baru.
    Mendukung laporan untuk post dan komentar.
    """
    post_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'id': 'report-post-input'
        }),
        label='ID Post'
    )
    
    comment_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'id': 'report-comment-input'
        }),
        label='ID Komentar'
    )

    class Meta:
        model = Report
        fields = ['category', 'description']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control',
                'id': 'report-category-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Jelaskan alasan pelaporan... (opsional)',
                'rows': 3,
                'maxlength': '500',
                'id': 'report-description-textarea'
            }),
        }
        labels = {
            'category': 'Kategori Laporan',
            'description': 'Deskripsi Tambahan',
        }
        help_texts = {
            'category': 'Pilih kategori yang paling sesuai',
            'description': 'Maksimal 500 karakter. Field ini opsional.',
        }

    def __init__(self, *args, **kwargs):
        self.reporter = kwargs.pop('reporter', None)
        super().__init__(*args, **kwargs)
        
        # Custom label untuk category choices
        self.fields['category'].choices = [
            ('', '-- Pilih Kategori --'),
            ('SARA', '🧩 Konten SARA (Suku, Agama, Ras, Antar-golongan)'),
            ('SPAM', '📢 Spam atau Iklan Tidak Sah'),
            ('NSFW', '🔞 Konten Tidak Senonoh (NSFW)'),
            ('OTHER', '❔ Lainnya'),
        ]

    def clean_description(self):
        """
        Validasi custom untuk description:
        - Sanitasi input
        - Validasi panjang
        """
        description = self.cleaned_data.get('description', '').strip()
        
        if description and len(description) > 500:
            raise ValidationError("Deskripsi maksimal 500 karakter.")
        
        # Sanitasi input
        return escape(description) if description else description

    def clean_post_id(self):
        """
        Validasi bahwa post exists dan tidak deleted
        """
        post_id = self.cleaned_data.get('post_id')
        if post_id:
            try:
                post = Post.objects.get(id=post_id, is_deleted=False)
                return post
            except Post.DoesNotExist:
                raise ValidationError("Post tidak ditemukan atau telah dihapus.")
        return None

    def clean_comment_id(self):
        """
        Validasi bahwa comment exists dan tidak deleted
        """
        comment_id = self.cleaned_data.get('comment_id')
        if comment_id:
            try:
                comment = Comment.objects.get(id=comment_id, is_deleted=False)
                return comment
            except Comment.DoesNotExist:
                raise ValidationError("Komentar tidak ditemukan atau telah dihapus.")
        return None

    def clean(self):
        """
        Validasi cross-field:
        - Harus ada post_id ATAU comment_id (tidak keduanya)
        - Reporter harus valid
        - Tidak boleh melaporkan konten sendiri
        """
        cleaned_data = super().clean()
        
        post = cleaned_data.get('post_id')
        comment = cleaned_data.get('comment_id')
        
        # Validasi: harus ada post atau comment
        if not post and not comment:
            raise ValidationError("Harus memilih post atau komentar untuk dilaporkan.")
        
        # Validasi: tidak boleh keduanya
        if post and comment:
            raise ValidationError("Hanya dapat melaporkan satu jenis konten.")
        
        # Validasi reporter
        if not self.reporter or not self.reporter.is_authenticated:
            raise ValidationError("Harus login untuk membuat laporan.")
        
        # Validasi: tidak boleh melaporkan konten sendiri
        if post and post.user == self.reporter:
            raise ValidationError("Tidak dapat melaporkan konten sendiri.")
        
        if comment and comment.user == self.reporter:
            raise ValidationError("Tidak dapat melaporkan komentar sendiri.")
        
        # Set content object untuk model
        if post:
            cleaned_data['post'] = post
        if comment:
            cleaned_data['comment'] = comment
        
        return cleaned_data

    def save(self, commit=True):
        """
        Override save untuk menambahkan reporter
        """
        report = super().save(commit=False)
        report.reporter = self.reporter
        
        # Set post atau comment dari cleaned_data
        if self.cleaned_data.get('post'):
            report.post = self.cleaned_data['post']
        if self.cleaned_data.get('comment'):
            report.comment = self.cleaned_data['comment']
        
        if commit:
            report.save()
        
        return report


class ReportUpdateForm(forms.ModelForm):
    """
    Form untuk mengupdate status laporan (admin only).
    """
    class Meta:
        model = Report
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control',
                'id': 'report-status-select'
            }),
        }
        labels = {
            'status': 'Status Laporan',
        }

    def __init__(self, *args, **kwargs):
        self.reviewer = kwargs.pop('reviewer', None)
        super().__init__(*args, **kwargs)
        
        # Custom status choices
        self.fields['status'].choices = [
            ('PENDING', '⏳ Menunggu Review'),
            ('REVIEWED', '🔍 Ditinjau'),
            ('RESOLVED', '✅ Selesai'),
        ]

    def clean_status(self):
        """
        Validasi custom untuk status update
        """
        status = self.cleaned_data.get('status')
        
        if status not in ['PENDING', 'REVIEWED', 'RESOLVED']:
            raise ValidationError("Status tidak valid.")
        
        return status

    def save(self, commit=True):
        """
        Override save untuk menambahkan reviewer dan timestamp
        """
        report = super().save(commit=False)
        
        # Jika status berubah menjadi REVIEWED, set reviewer dan timestamp
        if report.status == 'REVIEWED' and not report.reviewed_by:
            report.reviewed_by = self.reviewer
        
        if commit:
            report.save()
        
        return report


class ReportAdminForm(forms.ModelForm):
    """
    Form khusus admin untuk manage semua laporan.
    """
    class Meta:
        model = Report
        fields = '__all__'
        widgets = {
            'reporter': forms.Select(attrs={'class': 'form-control'}),
            'post': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'reviewed_by': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_reporter(self):
        """Validasi reporter"""
        reporter = self.cleaned_data.get('reporter')
        if not reporter or not reporter.is_active:
            raise ValidationError("Reporter harus active dan valid.")
        return reporter

    def clean(self):
        """
        Validasi cross-field untuk admin form
        """
        cleaned_data = super().clean()
        
        post = cleaned_data.get('post')
        comment = cleaned_data.get('comment')
        
        if not post and not comment:
            raise ValidationError("Laporan harus terkait post atau komentar.")
        
        if post and comment:
            raise ValidationError("Laporan hanya boleh terkait satu jenis konten.")
        
        return cleaned_data


class ReportFilterForm(forms.Form):
    """
    Form untuk filtering laporan (admin dashboard).
    """
    STATUS_CHOICES = [
        ('', 'Semua Status'),
        ('PENDING', 'Menunggu Review'),
        ('REVIEWED', 'Ditinjau'),
        ('RESOLVED', 'Selesai'),
    ]
    
    CATEGORY_CHOICES = [
        ('', 'Semua Kategori'),
        ('SARA', 'Konten SARA'),
        ('SPAM', 'Spam'),
        ('NSFW', 'Konten Tidak Senonoh'),
        ('OTHER', 'Lainnya'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'filter-status-select'
        }),
        label='Filter Status'
    )
    
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'filter-category-select'
        }),
        label='Filter Kategori'
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'filter-date-from'
        }),
        label='Dari Tanggal'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'filter-date-to'
        }),
        label='Sampai Tanggal'
    )

    def clean_date_from(self):
        """Validasi date_from"""
        date_from = self.cleaned_data.get('date_from')
        return date_from

    def clean_date_to(self):
        """Validasi date_to"""
        date_to = self.cleaned_data.get('date_to')
        return date_to

    def clean(self):
        """
        Validasi bahwa date_from tidak boleh setelah date_to
        """
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Tanggal 'Dari' tidak boleh setelah tanggal 'Sampai'.")
        
        return cleaned_data