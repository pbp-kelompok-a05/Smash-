# report/models.py
from datetime import timezone
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Report(models.Model):
    """
    Model untuk menyimpan laporan konten tidak pantas.
    Superuser dapat mengelola semua laporan.
    """
    REPORT_CATEGORIES = [
        ('SARA', 'Konten SARA'),
        ('SPAM', 'Spam'),
        ('NSFW', 'Konten Tidak Senonoh'),
        ('OTHER', 'Lainnya'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Menunggu Review'),
        ('REVIEWED', 'Ditinjau'),
        ('RESOLVED', 'Selesai'),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Pelapor",
        related_name="reports_made"
    )
    post = models.ForeignKey(
        'post.Post',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Post Dilaporkan",
        related_name="reports"
    )
    comment = models.ForeignKey(
        'comment.Comment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Komentar Dilaporkan",
        related_name="reports"
    )
    category = models.CharField(
        max_length=10,
        choices=REPORT_CATEGORIES,
        verbose_name="Kategori Laporan"
    )
    description = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="Deskripsi Tambahan"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Status Laporan"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Waktu Dilaporkan"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Waktu Ditinjau"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Ditinjau Oleh",
        related_name="reports_reviewed"
    )

    class Meta:
        verbose_name = "Laporan"
        verbose_name_plural = "Laporan"
        ordering = ['-created_at']
        permissions = [
            ("manage_all_reports", "Can manage all reports"),  # Hak akses superuser
        ]

    def __str__(self):
        return f"Laporan {self.category} oleh {self.reporter.username}"

    def clean(self):
        """Validasi: Laporan harus terkait post ATAU komentar"""
        from django.core.exceptions import ValidationError
        if not self.post and not self.comment:
            raise ValidationError("Laporan harus terkait dengan post atau komentar.")
        if self.post and self.comment:
            raise ValidationError("Laporan hanya boleh terkait satu jenis konten.")

    def save(self, *args, **kwargs):
        """Catat waktu review saat status berubah"""
        if self.status == 'REVIEWED' and not self.reviewed_at:
            self.reviewed_at = timezone.now()
        super().save(*args, **kwargs)