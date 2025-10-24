from django.db import models
from django.contrib.auth.models import User

class Report(models.Model):
    # Status pilihan untuk laporan
    STATUS_CHOICES = [
        ('pending', 'Menunggu Review'),
        ('under_review', 'Sedang Ditinjau'),
        ('resolved', 'Selesai'),
        ('dismissed', 'Ditolak'),
    ]

    # Kategori pelanggaran
    CATEGORY_CHOICES = [
        ('sara', 'SARA'),
        ('spam', 'Spam'),
        ('inappropriate', 'Konten Tidak Senonoh'),
        ('other', 'Lainnya'),
    ]

    # Jenis konten yang dilaporkan
    CONTENT_TYPE_CHOICES = [
        ('post', 'Post'),
        ('comment', 'Komentar'),
    ]

    # Identifikasi konten yang dilaporkan
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField()  # ID dari post/komentar
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_reports')
    
    # Detail laporan
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)  # Deskripsi tambahan
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin handler
    handled_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='handled_reports'
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']  # Urutan default: laporan terbaru pertama
        indexes = [
            models.Index(fields=['content_type', 'content_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Laporan {self.content_type} #{self.content_id} oleh {self.reporter.username}"