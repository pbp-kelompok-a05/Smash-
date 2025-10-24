import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.urls import reverse
from django.core.exceptions import ValidationError


class Report(models.Model):
    """
    Model untuk sistem pelaporan konten forum padel.
    
    Mendukung CRUD lengkap dengan fitur:
    - Create: Pengguna mengirim laporan melalui tombol report
    - Read: Admin membaca keluhan dan meninjau laporan
    - Update: Admin memperbarui status laporan
    - Delete: Admin menghapus laporan setelah verifikasi selesai
    
    Laporan dapat dibuat untuk:
    - Post forum (ForumPost)
    - Komentar (Comment)
    - Konten lain yang mendukung GenericForeignKey
    """
    
    # Status choices untuk tracking progress laporan
    STATUS_PENDING = 'pending'
    STATUS_UNDER_REVIEW = 'under_review'
    STATUS_RESOLVED = 'resolved'
    STATUS_REJECTED = 'rejected'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Menunggu Review'),
        (STATUS_UNDER_REVIEW, 'Sedang Ditinjau'),
        (STATUS_RESOLVED, 'Terselesaikan'),
        (STATUS_REJECTED, 'Ditolak'),
    ]
    
    # Reason categories khusus untuk konten SARA dan tidak pantas
    REASON_SARA = 'sara'
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_INAPPROPRIATE = 'inappropriate'
    REASON_COPYRIGHT = 'copyright'
    REASON_OTHER = 'other'
    
    REASON_CHOICES = [
        (REASON_SARA, 'Konten SARA (Suku, Agama, Ras, Antar-golongan)'),
        (REASON_SPAM, 'Spam atau iklan tidak relevan'),
        (REASON_HARASSMENT, 'Pelecehan atau bullying'),
        (REASON_INAPPROPRIATE, 'Konten tidak pantas/eksplisit'),
        (REASON_COPYRIGHT, 'Pelanggaran hak cipta'),
        (REASON_OTHER, 'Lainnya'),
    ]

    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reporter information
    reporter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name='Pelapor'
    )
    
    # Generic foreign key untuk konten yang dilaporkan (Post atau Comment)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name='Jenis Konten')
    object_id = models.UUIDField(verbose_name='ID Konten')  # Changed to UUID to match Post and Comment
    reported_object = GenericForeignKey('content_type', 'object_id')
    
    # Report details    
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default=REASON_OTHER,
        verbose_name='Alasan Pelaporan'
    )
    
    description = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name='Deskripsi Tambahan',
        help_text='Jelaskan secara detail mengapa konten ini dilaporkan (maks 1000 karakter)'
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Status Laporan'
    )
    
    # Evidence fields untuk mendukung laporan
    evidence_image = models.ImageField(
        upload_to='report_evidence/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name='Bukti Gambar',
        help_text='Unggah bukti pendukung (opsional)'
    )
    
    evidence_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Tautan Bukti',
        help_text='Tautan ke bukti pendukung (opsional)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Dibuat Pada'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Diperbarui Pada'
    )
    
    # Admin/moderation fields
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_resolved',
        verbose_name='Diselesaikan Oleh'
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Diselesaikan Pada'
    )
    
    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Catatan Admin',
        help_text='Catatan internal untuk moderator'
    )
    
    # Action taken fields
    action_taken = models.TextField(
        blank=True,
        null=True,
        verbose_name='Tindakan yang Diambil',
        help_text='Deskripsi tindakan yang dilakukan terhadap konten yang dilaporkan'
    )
    
    is_anonymous = models.BooleanField(
        default=False,
        verbose_name='Laporan Anonim',
        help_text='Jika dicentang, identitas pelapor tidak akan ditampilkan'
    )

    class Meta:
        verbose_name = 'Laporan'
        verbose_name_plural = 'Laporan'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['reporter', 'created_at']),
            models.Index(fields=['reason', 'status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'content_type', 'object_id'],
                name='unique_report_per_user_content',
                condition=models.Q(status__in=['pending', 'under_review'])
            )
        ]

    def __str__(self):
        object_type = self.get_reported_content_type()
        status_display = self.get_status_display()
        return f"Laporan {object_type} oleh {self.reporter.username} - {status_display}"

    def clean(self):
        """
        Validasi custom untuk model Report
        """
        # Validasi bahwa user tidak melaporkan konten milik sendiri
        if hasattr(self.reported_object, 'author') and self.reported_object.author == self.reporter:
            raise ValidationError("Anda tidak dapat melaporkan konten yang Anda buat sendiri.")
        
        # Validasi evidence: tidak boleh kedua-duanya diisi
        if self.evidence_image and self.evidence_url:
            raise ValidationError("Hanya boleh mengunggah gambar atau memasukkan tautan, tidak kedua-duanya.")
        
        # Validasi description untuk alasan SARA
        if self.reason == self.REASON_SARA and (not self.description or len(self.description.strip()) < 10):
            raise ValidationError({
                'description': 'Harap jelaskan secara detail untuk laporan konten SARA (minimal 10 karakter).'
            })

    def save(self, *args, **kwargs):
        """
        Override save untuk auto-update resolved_at dan validasi
        """
        # Auto-update resolved_at ketika status berubah menjadi resolved
        if self.status == self.STATUS_RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status != self.STATUS_RESOLVED and self.resolved_at:
            self.resolved_at = None
        
        # Set resolved_by jika status diubah ke resolved oleh admin
        if self.status == self.STATUS_RESOLVED and not self.resolved_by and hasattr(self, '_current_user'):
            self.resolved_by = self._current_user
        
        super().save(*args, **kwargs)

    # === CRUD OPERATIONS ===
    def mark_as_reviewed(self, user=None):
        """Menandai laporan sedang ditinjau"""
        self.status = self.STATUS_UNDER_REVIEW
        if user:
            self._current_user = user
        self.save(update_fields=['status', 'updated_at'])

    def resolve(self, user=None, notes=None, action_taken=None):
        """Menyelesaikan laporan"""
        self.status = self.STATUS_RESOLVED
        if user:
            self._current_user = user
        if notes:
            self.admin_notes = notes
        if action_taken:
            self.action_taken = action_taken
        self.save()

    def reject(self, user=None, notes=None):
        """Menolak laporan"""
        self.status = self.STATUS_REJECTED
        if user:
            self._current_user = user
        if notes:
            self.admin_notes = notes
        self.save()

    def reopen(self):
        """Membuka kembali laporan yang telah ditutup"""
        self.status = self.STATUS_PENDING
        self.resolved_by = None
        self.resolved_at = None
        self.save()

    # === UTILITY METHODS ===
    def get_reported_content_type(self):
        """Mendapatkan tipe konten yang dilaporkan dalam bahasa Indonesia"""
        model_class = self.content_type.model_class()
        if model_class.__name__ == 'ForumPost':
            return 'Post Forum'
        elif model_class.__name__ == 'Comment':
            return 'Komentar'
        else:
            return self.content_type.model

    def get_reported_content_preview(self):
        """Mendapatkan preview konten yang dilaporkan"""
        if hasattr(self.reported_object, 'content'):
            content = self.reported_object.content
            return content[:100] + '...' if len(content) > 100 else content
        elif hasattr(self.reported_object, 'title'):
            return self.reported_object.title
        return str(self.reported_object)

    def get_absolute_url(self):
        """URL untuk mengakses detail laporan"""
        return reverse('report_detail', kwargs={'pk': self.id})

    def get_admin_url(self):
        """URL untuk admin interface"""
        return reverse('admin:report_report_change', args=[self.id])

    # === PERMISSION CHECKS ===
    def can_view(self, user):
        """Cek apakah user dapat melihat laporan ini"""
        if user.is_staff or user.is_superuser:
            return True
        return user == self.reporter

    def can_edit(self, user):
        """Cek apakah user dapat mengedit laporan ini"""
        if user.is_staff or user.is_superuser:
            return True
        # User biasa hanya bisa edit laporan mereka sendiri yang masih pending
        return user == self.reporter and self.status == self.STATUS_PENDING

    def can_delete(self, user):
        """Cek apakah user dapat menghapus laporan ini"""
        if user.is_staff or user.is_superuser:
            return True
        # User biasa hanya bisa hapus laporan mereka sendiri yang masih pending
        return user == self.reporter and self.status == self.STATUS_PENDING

    def can_resolve(self, user):
        """Cek apakah user dapat menyelesaikan laporan ini"""
        return user.is_staff or user.is_superuser

    # === PROPERTIES ===
    @property
    def is_resolved(self):
        """Cek apakah laporan sudah diselesaikan"""
        return self.status in [self.STATUS_RESOLVED, self.STATUS_REJECTED]

    @property
    def is_pending(self):
        """Cek apakah laporan masih menunggu"""
        return self.status == self.STATUS_PENDING

    @property
    def days_since_created(self):
        """Jumlah hari sejak laporan dibuat"""
        return (timezone.now() - self.created_at).days

    @property
    def reporter_display_name(self):
        """Nama pelapor untuk ditampilkan"""
        if self.is_anonymous:
            return 'Anonim'
        return self.reporter.username

    # === CLASS METHODS ===
    @classmethod
    def get_pending_reports(cls):
        """Mendapatkan semua laporan yang masih pending"""
        return cls.objects.filter(status=cls.STATUS_PENDING)

    @classmethod
    def get_reports_by_user(cls, user):
        """Mendapatkan semua laporan oleh user tertentu"""
        return cls.objects.filter(reporter=user)

    @classmethod
    def get_reports_for_content(cls, content_type, object_id):
        """Mendapatkan semua laporan untuk konten tertentu"""
        return cls.objects.filter(
            content_type=content_type,
            object_id=object_id
        ).exclude(status=cls.STATUS_REJECTED)

    @classmethod
    def create_report(cls, reporter, reported_object, reason, description='', is_anonymous=False, evidence_image=None, evidence_url=None):
        """
        Method untuk membuat laporan baru dengan validasi
        
        Args:
            reporter: User yang membuat laporan
            reported_object: Objek yang dilaporkan (Post/Comment)
            reason: Alasan pelaporan
            description: Deskripsi tambahan
            is_anonymous: Apakah laporan anonim
            evidence_image: Gambar bukti
            evidence_url: Tautan bukti
        """
        content_type = ContentType.objects.get_for_model(reported_object)
        
        # Cek apakah user sudah melaporkan konten ini yang masih pending
        existing_report = cls.objects.filter(
            reporter=reporter,
            content_type=content_type,
            object_id=reported_object.id,
            status__in=[cls.STATUS_PENDING, cls.STATUS_UNDER_REVIEW]
        ).first()
        
        if existing_report:
            raise ValidationError("Anda sudah melaporkan konten ini sebelumnya. Laporan Anda sedang ditinjau.")
        
        report = cls(
            reporter=reporter,
            content_type=content_type,
            object_id=reported_object.id,
            reason=reason,
            description=description,
            is_anonymous=is_anonymous,
            evidence_image=evidence_image,
            evidence_url=evidence_url
        )
        
        report.full_clean()
        report.save()
        return report


class ReportSettings(models.Model):
    """
    Model untuk pengaturan sistem pelaporan
    """
    # Pengaturan umum
    max_reports_per_day = models.PositiveIntegerField(
        default=5,
        verbose_name='Maksimal Laporan per Hari per User',
        help_text='Batas jumlah laporan yang bisa dibuat user dalam sehari'
    )
    
    auto_reject_after_days = models.PositiveIntegerField(
        default=30,
        verbose_name='Auto Reject setelah Hari',
        help_text='Laporan pending otomatis ditolak setelah hari tertentu'
    )
    
    # Notifikasi
    notify_admins_on_report = models.BooleanField(
        default=True,
        verbose_name='Notifikasi Admin pada Laporan Baru'
    )
    
    notify_reporter_on_update = models.BooleanField(
        default=True,
        verbose_name='Notifikasi Pelapor pada Update'
    )
    
    # Konten yang bisa dilaporkan
    allow_anonymous_reports = models.BooleanField(
        default=False,
        verbose_name='Izinkan Laporan Anonim'
    )
    
    require_evidence = models.BooleanField(
        default=False,
        verbose_name='Wajibkan Bukti untuk Laporan Tertentu'
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Pengaturan Pelaporan'
        verbose_name_plural = 'Pengaturan Pelaporan'
    
    def __str__(self):
        return 'Pengaturan Sistem Pelaporan'
    
    def save(self, *args, **kwargs):
        # Hanya boleh ada satu instance pengaturan
        self.__class__.objects.exclude(id=self.id).delete()
        super().save(*args, **kwargs)