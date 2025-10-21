from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

class Report(models.Model):
    # Status choices
    # Ide : Aplikasi web nantinya tidak akan secara langsung mengkonfirmasi laporan yang masuk, tetapi akan mengeceknya terlebih dahuku
    STATUS_PENDING = 'pending'
    STATUS_UNDER_REVIEW = 'under_review'
    STATUS_RESOLVED = 'resolved'
    STATUS_REJECTED = 'rejected'
    
    # List kategori status laporan dikonfirmasi oleh web (akan di set oleh admin)
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    
    # Reason categories
    # Ide : Aplikasi web nantinya akan menyediakan pilihan atau alasan laporan tersebut dibuat oleh user
    # Ide tambahannya, user dapat memasukkan alasan spesifik kenapa laporan tersebut diajukan 
    REASON_SPAM = 'spam'
    REASON_HARASSMENT = 'harassment'
    REASON_INAPPROPRIATE = 'inappropriate'
    REASON_OTHER = 'other'
    
    # List untuk pilihan alasan laporan dibuat
    REASON_CHOICES = [
        (REASON_SPAM, 'Spam atau iklan'),
        (REASON_HARASSMENT, 'Pelecehan atau bullying'),
        (REASON_INAPPROPRIATE, 'Konten tidak pantas'),
        (REASON_OTHER, 'Lainnya'),
    ]

    # Reporter information
    # Mengambil identitas dari user yang membuat laporan 
    # ON DELETE CASCADE berfungsi agar ketika objek dihapus, maka objek terkait akan dihapus secara otomatis sehingga tidak melanggar referential integrity
    reporter = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name='Pelapor'
    )
    
    # Generic foreign key untuk konten yang dilaporkan
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    reported_object = GenericForeignKey('content_type', 'object_id')
    
    # Report details
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default=REASON_OTHER,
        verbose_name='Alasan Pelaporan'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='Deskripsi Tambahan',
        help_text='Jelaskan secara detail mengapa konten ini dilaporkan'
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name='Status Laporan'
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

    class Meta:
        verbose_name = 'Laporan'
        verbose_name_plural = 'Laporan'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Laporan oleh {self.reporter.username} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Auto-update resolved_at when status changes to resolved
        if self.status == self.STATUS_RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        elif self.status != self.STATUS_RESOLVED:
            self.resolved_at = None
            
        super().save(*args, **kwargs)

    def get_reported_content_type(self):
        """Mendapatkan tipe konten yang dilaporkan"""
        return self.content_type.model_class()._meta.verbose_name.title()

    def is_resolved(self):
        """Cek apakah laporan sudah diselesaikan"""
        return self.status in [self.STATUS_RESOLVED, self.STATUS_REJECTED]