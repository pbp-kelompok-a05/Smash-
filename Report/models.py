# report/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse

class Report(models.Model):
    """
    MODEL: Report
    MODUL: Report 🚩
    DEVELOPER: Christna
    
    DESKRIPSI:
    Model untuk merepresentasikan laporan pengguna terhadap konten tidak pantas.
    Mendukung pelaporan post dan komentar dengan berbagai alasan.
    
    FUNGSI UTAMA:
    - Menyimpan laporan dari pengguna
    - Melacak status penanganan oleh admin
    - Menyediakan sistem verifikasi dan resolusi
    
    CRUD OPERATIONS:
    - Create: Pengguna mengirim laporan
    - Read: Admin membaca dan meninjau laporan
    - Update: Admin memperbarui status laporan
    - Delete: Admin menghapus laporan setelah selesai
    
    RELASI EKSTERNAL:
    - User (pelapor)
    - Post (post yang dilaporkan) [di app post]
    - Comment (komentar yang dilaporkan) [di app comment]
    """
    
    # Choice options
    CONTENT_TYPE_CHOICES = [
        ('POST', 'Postingan'),
        ('COMMENT', 'Komentar'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', '🟡 Menunggu Review'),
        ('UNDER_REVIEW', '🔵 Sedang Ditinjau'),
        ('RESOLVED', '🟢 Selesai'),
        ('REJECTED', '🔴 Ditolak'),
    ]
    
    VIOLATION_CHOICES = [
        ('SARA', 'Konten SARA (Suku, Agama, Ras, Antar-golongan)'),
        ('SPAM', 'Spam atau Konten Promosi Ilegal'),
        ('INAPPROPRIATE', 'Konten Tidak Senonoh/Pornografi'),
        ('HARASSMENT', 'Pelecehan atau Perundungan'),
        ('HATE_SPEECH', 'Ujaran Kebencian'),
        ('MISINFORMATION', 'Informasi Palsu/Misinformasi'),
        ('COPYRIGHT', 'Pelanggaran Hak Cipta'),
        ('OTHER', 'Lainnya'),
    ]
    
    ACTION_CHOICES = [
        ('NO_ACTION', 'Tidak Ada Tindakan'),
        ('CONTENT_REMOVED', 'Konten Dihapus'),
        ('USER_WARNED', 'Pengguna Diperingatkan'),
        ('USER_SUSPENDED', 'Pengguna Ditangguhkan'),
        ('USER_BANNED', 'Pengguna Diblokir'),
    ]

    # Fields
    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_made',
        verbose_name="Pelapor"
    )
    
    post = models.ForeignKey(
        'post.Post',  # Import dari app post
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name="Postingan Dilaporkan"
    )
    
    comment = models.ForeignKey(
        'comment.Comment',  # Import dari app comment
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name="Komentar Dilaporkan"
    )
    
    content_type = models.CharField(
        max_length=7,
        choices=CONTENT_TYPE_CHOICES,
        verbose_name="Jenis Konten"
    )
    
    reason = models.CharField(
        max_length=20,
        choices=VIOLATION_CHOICES,
        verbose_name="Alasan Pelaporan"
    )
    
    description = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name="Deskripsi Detail",
        help_text="Jelaskan secara detail mengapa konten ini melanggar"
    )
    
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Status Laporan"
    )
    
    admin_action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        blank=True,
        verbose_name="Tindakan Admin"
    )
    
    admin_notes = models.TextField(
        max_length=1000,
        blank=True,
        verbose_name="Catatan Admin",
        help_text="Catatan internal untuk penanganan laporan"
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports',
        verbose_name="Diselesaikan Oleh"
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Diselesaikan Pada"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dilaporkan Pada"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Diupdate Pada"
    )

    class Meta:
        """Konfigurasi metadata untuk model Report"""
        db_table = 'report_reports'
        ordering = ['-created_at']
        verbose_name = "Laporan"
        verbose_name_plural = "Laporan"
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['reporter', 'created_at']),
            models.Index(fields=['content_type']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['reporter', 'post'],
                condition=models.Q(post__isnull=False),
                name='unique_report_per_post'
            ),
            models.UniqueConstraint(
                fields=['reporter', 'comment'],
                condition=models.Q(comment__isnull=False),
                name='unique_report_per_comment'
            ),
        ]

    def clean(self):
        """
        VALIDASI CUSTOM:
        - Harus melaporkan post ATAU komentar, tidak boleh keduanya
        - Content type harus sesuai dengan objek yang dilaporkan
        - Tidak boleh melaporkan konten sendiri
        - Validasi status dan action consistency
        """
        super().clean()
        
        # Validasi: harus melaporkan post atau komentar (tidak keduanya)
        if not self.post and not self.comment:
            raise ValidationError({
                'post': 'Harus memilih post atau komentar yang dilaporkan.',
                'comment': 'Harus memilih post atau komentar yang dilaporkan.'
            })
        
        if self.post and self.comment:
            raise ValidationError({
                'post': 'Hanya boleh melaporkan satu jenis konten.',
                'comment': 'Hanya boleh melaporkan satu jenis konten.'
            })
        
        # Validasi: content type harus sesuai
        if self.post and self.content_type != 'POST':
            raise ValidationError({
                'content_type': 'Content type harus "POST" ketika melaporkan postingan.'
            })
        
        if self.comment and self.content_type != 'COMMENT':
            raise ValidationError({
                'content_type': 'Content type harus "COMMENT" ketika melaporkan komentar.'
            })
        
        # Validasi: tidak boleh melaporkan konten sendiri
        if self.post and self.post.user == self.reporter:
            raise ValidationError({
                'post': 'Tidak boleh melaporkan postingan sendiri.'
            })
        
        if self.comment and self.comment.user == self.reporter:
            raise ValidationError({
                'comment': 'Tidak boleh melaporkan komentar sendiri.'
            })
        
        # Validasi: resolved report harus memiliki resolved_by dan resolved_at
        if self.status in ['RESOLVED', 'REJECTED'] and not self.resolved_by:
            raise ValidationError({
                'status': 'Laporan yang diselesaikan harus memiliki admin yang menanganinya.'
            })

    def save(self, *args, **kwargs):
        """Override save method untuk validasi custom dan auto-fields"""
        # Auto-set content_type berdasarkan objek yang dilaporkan
        if self.post:
            self.content_type = 'POST'
        elif self.comment:
            self.content_type = 'COMMENT'
        
        # Auto-set resolved_at ketika status berubah ke RESOLVED/REJECTED
        if self.status in ['RESOLVED', 'REJECTED'] and not self.resolved_at:
            from django.utils import timezone
            self.resolved_at = timezone.now()
        
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Representasi string untuk Report"""
        return f"Laporan {self.content_type} oleh {self.reporter.username} - {self.get_status_display()}"

    # Properties untuk business logic
    @property
    def reported_content(self):
        """Mendapatkan objek konten yang dilaporkan"""
        return self.post if self.post else self.comment

    @property
    def reported_user(self):
        """Mendapatkan user pembuat konten yang dilaporkan"""
        if self.post:
            return self.post.user
        elif self.comment:
            return self.comment.user
        return None

    @property
    def is_resolved(self):
        """Cek apakah laporan sudah diselesaikan"""
        return self.status in ['RESOLVED', 'REJECTED']

    @property
    def is_pending(self):
        """Cek apakah laporan masih menunggu review"""
        return self.status == 'PENDING'

    @property
    def days_since_reported(self):
        """Menghitung berapa hari sejak laporan dibuat"""
        from django.utils import timezone
        return (timezone.now() - self.created_at).days

    # Method untuk workflow management
    def mark_as_under_review(self, admin_user):
        """Menandai laporan sedang ditinjau"""
        self.status = 'UNDER_REVIEW'
        if admin_user:
            self.resolved_by = admin_user
        self.save()

    def mark_as_resolved(self, admin_user, action='NO_ACTION', notes=''):
        """Menandai laporan sebagai selesai"""
        self.status = 'RESOLVED'
        self.resolved_by = admin_user
        self.admin_action = action
        if notes:
            self.admin_notes = notes
        self.save()

    def mark_as_rejected(self, admin_user, notes=''):
        """Menandai laporan ditolak"""
        self.status = 'REJECTED'
        self.resolved_by = admin_user
        self.admin_action = 'NO_ACTION'
        if notes:
            self.admin_notes = notes
        self.save()

    def can_be_handled_by(self, user):
        """Cek apakah user dapat menangani laporan ini"""
        return user.is_staff or user.has_perm('report.handle_report')

    def get_absolute_url(self):
        """URL untuk mengakses detail laporan"""
        return reverse('report:report-detail', kwargs={'pk': self.pk})