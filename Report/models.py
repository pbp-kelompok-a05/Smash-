import uuid
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone


class Report(models.Model):
    """
    Model untuk merepresentasikan laporan terhadap post atau komentar.
    Mendukung pelaporan untuk berbagai jenis konten (Post, Comment, dll).
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
    
    # Kategori pelaporan
    CATEGORY_SARA = 'sara'
    CATEGORY_SPAM = 'spam'
    CATEGORY_INAPPROPRIATE = 'inappropriate'
    CATEGORY_HARASSMENT = 'harassment'
    CATEGORY_OTHER = 'other'
    
    CATEGORY_CHOICES = [
        (CATEGORY_SARA, 'SARA (Suku, Agama, Ras, Antar-golongan)'),
        (CATEGORY_SPAM, 'Spam atau Iklan Tidak Sah'),
        (CATEGORY_INAPPROPRIATE, 'Konten Tidak Senonoh'),
        (CATEGORY_HARASSMENT, 'Pelecehan atau Perundungan'),
        (CATEGORY_OTHER, 'Lainnya'),
    ]

    # Primary Key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Report ID"
    )
    
    # Reporter (user yang melaporkan)
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submitted_reports',
        verbose_name="Pelapor"
    )
    
    # Generic Foreign Key untuk menghandle report terhadap Post atau Comment
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Jenis Konten"
    )
    object_id = models.UUIDField(
        verbose_name="ID Objek"
    )
    reported_object = GenericForeignKey(
        'content_type', 
        'object_id'
    )
    
    # Kategori dan alasan pelaporan
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name="Kategori Pelaporan"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Deskripsi Tambahan",
        help_text="Jelaskan secara detail alasan pelaporan"
    )
    
    # Status dan tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="Status Laporan"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dilaporkan pada"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Diperbarui pada"
    )
    
    # Admin fields
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_reports',
        verbose_name="Ditinjau oleh"
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ditinjau pada"
    )
    
    admin_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Catatan Admin",
        help_text="Catatan internal untuk tim moderasi"
    )
    
    # Soft delete flag
    is_resolved = models.BooleanField(
        default=False,
        verbose_name="Terselesaikan?",
        help_text="Laporan dianggap selesai dan bisa diarsipkan"
    )

    class Meta:
        """Konfigurasi tambahan untuk model Report"""
        ordering = ['-created_at']
        verbose_name = "Report"
        verbose_name_plural = "Reports"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['reporter', 'created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'content_type', 'object_id'],
                name='unique_report_per_user_per_object'
            )
        ]

    def __str__(self):
        """Representasi string untuk objek Report"""
        return f"Report #{self.id.hex[:8]} - {self.get_category_display()} by {self.reporter.username}"

    def get_reported_content_type(self):
        """Mendapatkan tipe konten yang dilaporkan dalam format yang mudah dibaca"""
        return self.content_type.model_class()._meta.verbose_name.title()

    def get_reported_object_str(self):
        """Mendapatkan string representasi dari objek yang dilaporkan"""
        return str(self.reported_object)

    def mark_as_reviewed(self, admin_user):
        """Menandai laporan sedang ditinjau oleh admin"""
        self.status = self.STATUS_UNDER_REVIEW
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.save()

    def mark_as_resolved(self, admin_user, notes=None):
        """Menandai laporan sebagai terselesaikan"""
        self.status = self.STATUS_RESOLVED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        self.is_resolved = True
        if notes:
            self.admin_notes = notes
        self.save()

    def mark_as_rejected(self, admin_user, notes=None):
        """Menandai laporan sebagai ditolak"""
        self.status = self.STATUS_REJECTED
        self.reviewed_by = admin_user
        self.reviewed_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save()

    def reopen_report(self):
        """Membuka kembali laporan yang sudah ditutup"""
        self.status = self.STATUS_PENDING
        self.is_resolved = False
        self.reviewed_by = None
        self.reviewed_at = None
        self.save()

    @property
    def is_pending(self):
        """Cek apakah laporan masih menunggu review"""
        return self.status == self.STATUS_PENDING

    @property
    def is_under_review(self):
        """Cek apakah laporan sedang ditinjau"""
        return self.status == self.STATUS_UNDER_REVIEW

    @property
    def days_since_reported(self):
        """Menghitung berapa hari sejak laporan dibuat"""
        return (timezone.now() - self.created_at).days

    @classmethod
    def get_pending_reports_count(cls):
        """Mendapatkan jumlah laporan yang masih pending"""
        return cls.objects.filter(status=cls.STATUS_PENDING, is_resolved=False).count()

    @classmethod
    def get_reports_for_object(cls, content_type, object_id):
        """Mendapatkan semua laporan untuk objek tertentu"""
        return cls.objects.filter(
            content_type=content_type, 
            object_id=object_id
        ).order_by('-created_at')


class ReportSettings(models.Model):
    """
    Model untuk menyimpan pengaturan sistem pelaporan.
    Bisa dikonfigurasi oleh admin.
    """
    # Threshold untuk auto-action
    auto_action_threshold = models.PositiveIntegerField(
        default=3,
        verbose_name="Threshold Auto Action",
        help_text="Jumlah laporan minimum untuk tindakan otomatis"
    )
    
    # Email notifications
    notify_admin_on_report = models.BooleanField(
        default=True,
        verbose_name="Notifikasi Admin pada Laporan Baru"
    )
    
    # Auto hide content
    auto_hide_on_threshold = models.BooleanField(
        default=True,
        verbose_name="Sembunyikan Konten Otomatis pada Threshold"
    )
    
    # Retention policy
    keep_resolved_reports_days = models.PositiveIntegerField(
        default=30,
        verbose_name="Menyimpan Laporan Terselesaikan (hari)",
        help_text="Laporan yang sudah resolved akan diarsipkan setelah hari ini"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Diperbarui oleh"
    )

    class Meta:
        verbose_name = "Report Settings"
        verbose_name_plural = "Report Settings"

    def __str__(self):
        return "Report System Settings"

    def save(self, *args, **kwargs):
        """Hanya boleh ada satu instance settings"""
        self.pk = 1
        super().save(*args, **kwargs)