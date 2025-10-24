from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from .models import Report, ReportSettings


class ReportForm(forms.ModelForm):
    """
    Form untuk membuat laporan baru oleh pengguna.
    
    Features:
    - Validasi XSS protection pada description
    - Validasi evidence (gambar atau URL, tidak kedua-duanya)
    - Validasi khusus untuk laporan SARA
    - AJAX compatible dengan error handling
    """
    
    # Field tambahan untuk konfirmasi
    confirm_report = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'required': 'required'
        }),
        label='Saya yakin dengan laporan ini dan memahami konsekuensinya',
        help_text='Dengan mencentang ini, Anda menyatakan bahwa laporan ini dibuat dengan itikad baik.'
    )
    
    class Meta:
        model = Report
        fields = ['reason', 'description', 'is_anonymous', 'evidence_image', 'evidence_url']
        
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required',
                'data-ajax-target': 'reason-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Jelaskan secara detail mengapa konten ini dilaporkan...',
                'data-min-chars': '10',
                'maxlength': '1000'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'data-ajax-target': 'anonymous-checkbox'
            }),
            'evidence_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-max-size': '5242880'  # 5MB
            }),
            'evidence_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/bukti...',
                'data-ajax-target': 'evidence-url'
            }),
        }
        
        labels = {
            'reason': 'Alasan Pelaporan *',
            'description': 'Deskripsi Tambahan',
            'is_anonymous': 'Laporkan secara anonim',
            'evidence_image': 'Unggah Bukti Gambar',
            'evidence_url': 'Tautan Bukti',
        }
        
        help_texts = {
            'reason': 'Pilih alasan utama mengapa Anda melaporkan konten ini.',
            'description': 'Jelaskan secara detail untuk membantu moderator memahami laporan Anda. (maks 1000 karakter)',
            'is_anonymous': 'Identitas Anda tidak akan ditampilkan kepada pemilik konten.',
            'evidence_image': 'Format: JPG, PNG, GIF. Maksimal 5MB.',
            'evidence_url': 'Tautan ke bukti pendukung seperti screenshot atau link relevan.',
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize form dengan custom settings
        """
        self.reported_object = kwargs.pop('reported_object', None)
        self.reporter = kwargs.pop('reporter', None)
        super().__init__(*args, **kwargs)
        
        # Set required fields
        self.fields['reason'].required = True
        
        # Dynamic help text untuk SARA
        self.fields['reason'].help_text += (
            " <strong>Khusus untuk laporan SARA: harap berikan penjelasan detail.</strong>"
        )

    def clean_description(self):
        """
        Clean dan validasi description:
        - Strip HTML tags untuk prevent XSS
        - Validasi panjang minimum untuk SARA
        - Validasi konten tidak kosong
        """
        description = self.cleaned_data.get('description', '').strip()
        
        # Strip HTML tags untuk prevent XSS
        cleaned_description = strip_tags(description)
        
        # Jika description kosong, return tanpa validasi lebih lanjut
        if not cleaned_description:
            return cleaned_description
        
        # Validasi panjang minimum untuk SARA
        reason = self.cleaned_data.get('reason')
        if reason == Report.REASON_SARA and len(cleaned_description) < 10:
            raise ValidationError(
                "Untuk laporan SARA, harap jelaskan secara detail (minimal 10 karakter)."
            )
        
        return cleaned_description

    def clean_evidence_image(self):
        """
        Validasi evidence image:
        - Size validation (max 5MB)
        - File type validation
        """
        evidence_image = self.cleaned_data.get('evidence_image')
        
        if evidence_image:
            # Validasi ukuran file (max 5MB)
            if evidence_image.size > 5 * 1024 * 1024:
                raise ValidationError("Ukuran file terlalu besar (maksimal 5MB)")
            
            # Validasi tipe file
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
            extension = evidence_image.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise ValidationError(
                    f"Format file tidak didukung. Gunakan: {', '.join(valid_extensions)}"
                )
        
        return evidence_image

    def clean_evidence_url(self):
        """
        Validasi evidence URL:
        - Format URL yang valid
        - Domain validation (optional)
        """
        evidence_url = self.cleaned_data.get('evidence_url', '').strip()
        
        if evidence_url:
            # Validasi format URL dasar
            if not evidence_url.startswith(('http://', 'https://')):
                raise ValidationError("Masukkan URL yang valid (dimulai dengan http:// atau https://)")
            
            # Validasi domain umum (optional)
            suspicious_domains = ['localhost', '127.0.0.1', 'example.com']
            if any(domain in evidence_url for domain in suspicious_domains):
                raise ValidationError("URL tidak valid.")
        
        return evidence_url

    def clean(self):
        """
        Validasi cross-field:
        - Evidence: hanya gambar atau URL, tidak kedua-duanya
        - Validasi reporter dan reported_object
        - Validasi duplicate reports
        """
        cleaned_data = super().clean()
        
        evidence_image = cleaned_data.get('evidence_image')
        evidence_url = cleaned_data.get('evidence_url')
        reason = cleaned_data.get('reason')
        description = cleaned_data.get('description', '')
        is_anonymous = cleaned_data.get('is_anonymous', False)

        # Validasi evidence: hanya satu yang boleh diisi
        if evidence_image and evidence_url:
            raise ValidationError({
                'evidence_image': "Pilih salah satu: unggah gambar atau masukkan tautan, tidak kedua-duanya.",
                'evidence_url': "Pilih salah satu: unggah gambar atau masukkan tautan, tidak kedua-duanya."
            })

        # Validasi khusus untuk laporan SARA
        if reason == Report.REASON_SARA:
            if not description or len(description.strip()) < 10:
                self.add_error(
                    'description',
                    "Untuk laporan SARA, harap berikan penjelasan detail (minimal 10 karakter)."
                )
            
            # Untuk SARA, evidence sangat disarankan
            if not evidence_image and not evidence_url:
                self.add_error(
                    'evidence_image',
                    "Untuk laporan SARA, sangat disarankan untuk menyertakan bukti pendukung."
                )

        # Validasi reporter dan reported_object
        if not self.reporter:
            raise ValidationError("Pengguna tidak valid.")
        
        if not self.reported_object:
            raise ValidationError("Konten yang dilaporkan tidak valid.")

        # Validasi: user tidak bisa melaporkan konten sendiri
        if hasattr(self.reported_object, 'author') and self.reported_object.author == self.reporter:
            raise ValidationError("Anda tidak dapat melaporkan konten yang Anda buat sendiri.")

        # Validasi duplicate report (jika diperlukan)
        if self.reporter and self.reported_object:
            try:
                from django.contrib.contenttypes.models import ContentType
                content_type = ContentType.objects.get_for_model(self.reported_object)
                
                existing_report = Report.objects.filter(
                    reporter=self.reporter,
                    content_type=content_type,
                    object_id=self.reported_object.id,
                    status__in=[Report.STATUS_PENDING, Report.STATUS_UNDER_REVIEW]
                ).exists()
                
                if existing_report:
                    raise ValidationError(
                        "Anda sudah melaporkan konten ini sebelumnya. Laporan Anda sedang ditinjau."
                    )
            except Exception:
                # Skip duplicate check jika ada error
                pass

        return cleaned_data

    def save(self, commit=True):
        """
        Override save untuk set reporter dan reported_object
        """
        instance = super().save(commit=False)
        
        if self.reporter:
            instance.reporter = self.reporter
        
        if self.reported_object:
            from django.contrib.contenttypes.models import ContentType
            instance.content_type = ContentType.objects.get_for_model(self.reported_object)
            instance.object_id = self.reported_object.id
        
        if commit:
            instance.save()
        
        return instance


class ReportAdminForm(forms.ModelForm):
    """
    Form untuk admin mengelola laporan.
    
    Features:
    - Semua field tersedia
    - Validasi status transitions
    - Auto-set resolved_by
    """
    
    # Field tambahan untuk actions cepat
    quick_action = forms.ChoiceField(
        required=False,
        choices=[
            ('', '--- Pilih Aksi Cepat ---'),
            ('mark_reviewed', 'Tandai Sedang Ditinjau'),
            ('resolve_remove', 'Selesaikan & Hapus Konten'),
            ('resolve_warning', 'Selesaikan & Beri Peringatan'),
            ('reject', 'Tolak Laporan'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-action': 'quick-action'
        }),
        label='Aksi Cepat'
    )
    
    # Field untuk notifikasi
    notify_reporter = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Kirim notifikasi ke pelapor',
        help_text='Pelapor akan mendapat email tentang update status laporan.'
    )
    
    class Meta:
        model = Report
        fields = '__all__'
        
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
                'data-ajax-target': 'status-select'
            }),
            'reason': forms.Select(attrs={
                'class': 'form-select',
                'readonly': 'readonly'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'readonly': 'readonly'
            }),
            'admin_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Catatan internal untuk moderator...'
            }),
            'action_taken': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Jelaskan tindakan yang dilakukan...'
            }),
            'resolved_by': forms.Select(attrs={
                'class': 'form-select'
            }),
            'resolved_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'reporter': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        
        labels = {
            'status': 'Status Laporan',
            'admin_notes': 'Catatan Admin',
            'action_taken': 'Tindakan yang Diambil',
            'resolved_by': 'Diselesaikan Oleh',
            'resolved_at': 'Diselesaikan Pada',
        }
        
        help_texts = {
            'admin_notes': 'Catatan internal yang tidak dilihat oleh pelapor.',
            'action_taken': 'Deskripsi tindakan yang akan ditampilkan ke pelapor.',
        }

    def __init__(self, *args, **kwargs):
        """
        Initialize form dengan custom settings untuk admin
        """
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        # Set resolved_by ke current user secara default
        if self.current_user and not self.instance.resolved_by:
            self.fields['resolved_by'].initial = self.current_user
        
        # Make some fields readonly untuk instance yang sudah ada
        if self.instance and self.instance.pk:
            readonly_fields = ['reporter', 'reason', 'description', 'evidence_image', 'evidence_url']
            for field in readonly_fields:
                if field in self.fields:
                    self.fields[field].widget.attrs['readonly'] = True
                    self.fields[field].widget.attrs['class'] = 'form-control-plaintext'

    def clean_status(self):
        """
        Validasi perubahan status
        """
        status = self.cleaned_data.get('status')
        old_status = self.instance.status if self.instance.pk else None
        
        # Validasi: hanya admin yang bisa mengubah status
        if status != old_status and not getattr(self, 'current_user', None):
            raise ValidationError("Hanya admin yang dapat mengubah status laporan.")
        
        return status

    def clean_resolved_by(self):
        """
        Validasi resolved_by
        """
        resolved_by = self.cleaned_data.get('resolved_by')
        status = self.cleaned_data.get('status')
        
        # Jika status resolved, resolved_by harus diisi
        if status == Report.STATUS_RESOLVED and not resolved_by:
            if self.current_user:
                resolved_by = self.current_user
            else:
                raise ValidationError("Harap tentukan admin yang menyelesaikan laporan.")
        
        return resolved_by

    def clean(self):
        """
        Validasi cross-field untuk admin form
        """
        cleaned_data = super().clean()
        
        status = cleaned_data.get('status')
        action_taken = cleaned_data.get('action_taken')
        quick_action = cleaned_data.get('quick_action')
        
        # Validasi: jika status resolved, action_taken harus diisi
        if status == Report.STATUS_RESOLVED and not action_taken and not quick_action:
            self.add_error(
                'action_taken',
                "Harap jelaskan tindakan yang dilakukan untuk laporan yang diselesaikan."
            )
        
        # Process quick action
        if quick_action:
            if quick_action == 'mark_reviewed':
                cleaned_data['status'] = Report.STATUS_UNDER_REVIEW
            elif quick_action == 'resolve_remove':
                cleaned_data['status'] = Report.STATUS_RESOLVED
                cleaned_data['action_taken'] = 'Konten telah dihapus karena melanggar aturan.'
            elif quick_action == 'resolve_warning':
                cleaned_data['status'] = Report.STATUS_RESOLVED
                cleaned_data['action_taken'] = 'Peringatan telah diberikan kepada pemilik konten.'
            elif quick_action == 'reject':
                cleaned_data['status'] = Report.STATUS_REJECTED
                cleaned_data['action_taken'] = 'Laporan ditolak karena tidak cukup bukti atau tidak melanggar aturan.'
        
        return cleaned_data

    def save(self, commit=True):
        """
        Override save untuk handle auto-fields
        """
        instance = super().save(commit=False)
        
        # Auto-set resolved_by jika status berubah ke resolved
        if instance.status == Report.STATUS_RESOLVED and not instance.resolved_by:
            instance.resolved_by = self.current_user
        
        # Set current user untuk tracking
        if hasattr(instance, '_current_user'):
            instance._current_user = self.current_user
        
        if commit:
            instance.save()
        
        return instance


class ReportSettingsForm(forms.ModelForm):
    """
    Form untuk pengaturan sistem pelaporan
    """
    
    class Meta:
        model = ReportSettings
        fields = '__all__'
        
        widgets = {
            'max_reports_per_day': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '50'
            }),
            'auto_reject_after_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '365'
            }),
            'notify_admins_on_report': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notify_reporter_on_update': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_anonymous_reports': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'require_evidence': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        
        labels = {
            'max_reports_per_day': 'Maksimal Laporan per Hari per User',
            'auto_reject_after_days': 'Auto Reject setelah Hari',
            'notify_admins_on_report': 'Notifikasi Admin pada Laporan Baru',
            'notify_reporter_on_update': 'Notifikasi Pelapor pada Update',
            'allow_anonymous_reports': 'Izinkan Laporan Anonim',
            'require_evidence': 'Wajibkan Bukti untuk Laporan Tertentu',
        }
        
        help_texts = {
            'max_reports_per_day': 'Batas jumlah laporan yang bisa dibuat user dalam sehari untuk mencegah spam.',
            'auto_reject_after_days': 'Laporan pending otomatis ditolak setelah hari tertentu (0 untuk non-aktif).',
            'notify_admins_on_report': 'Admin akan menerima email ketika ada laporan baru.',
            'notify_reporter_on_update': 'Pelapor akan menerima email ketika status laporan berubah.',
            'allow_anonymous_reports': 'User dapat memilih untuk melaporkan secara anonim.',
            'require_evidence': 'User wajib menyertakan bukti untuk laporan SARA dan hak cipta.',
        }

    def clean_max_reports_per_day(self):
        """Validasi max reports per day"""
        max_reports = self.cleaned_data.get('max_reports_per_day')
        if max_reports < 1:
            raise ValidationError("Nilai harus lebih besar dari 0.")
        if max_reports > 50:
            raise ValidationError("Nilai tidak boleh lebih dari 50.")
        return max_reports

    def clean_auto_reject_after_days(self):
        """Validasi auto reject days"""
        days = self.cleaned_data.get('auto_reject_after_days')
        if days < 0:
            raise ValidationError("Nilai tidak boleh negatif.")
        if days > 365:
            raise ValidationError("Nilai tidak boleh lebih dari 365 hari.")
        return days


class ReportSearchForm(forms.Form):
    """
    Form untuk pencarian dan filter laporan (admin)
    """
    
    STATUS_CHOICES = [('', 'Semua Status')] + Report.STATUS_CHOICES
    REASON_CHOICES = [('', 'Semua Alasan')] + Report.REASON_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-filter': 'status'
        })
    )
    
    reason = forms.ChoiceField(
        choices=REASON_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-filter': 'reason'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Dari tanggal...'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Sampai tanggal...'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari berdasarkan pelapor atau deskripsi...',
            'data-ajax-search': 'true'
        })
    )

    def clean_date_from(self):
        date_from = self.cleaned_data.get('date_from')
        if date_from:
            from django.utils import timezone
            if date_from > timezone.now().date():
                raise ValidationError("Tanggal tidak boleh di masa depan.")
        return date_from

    def clean_date_to(self):
        date_to = self.cleaned_data.get('date_to')
        if date_to:
            from django.utils import timezone
            if date_to > timezone.now().date():
                raise ValidationError("Tanggal tidak boleh di masa depan.")
        return date_to

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError({
                'date_from': "Tanggal 'dari' tidak boleh setelah tanggal 'sampai'.",
                'date_to': "Tanggal 'sampai' tidak boleh sebelum tanggal 'dari'."
            })
        
        return cleaned_data