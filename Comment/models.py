# comment/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Comment(models.Model):
    """
    MODEL: Comment
    MODUL: Komentar 💬
    DEVELOPER: Nathan
    
    DESKRIPSI:
    Model untuk merepresentasikan komentar pengguna pada postingan.
    Mendukung teks dan emoji, dengan sistem like dan reply.
    
    FUNGSI UTAMA:
    - Menyimpan komentar pada post
    - Mengelola sistem reply/thread
    - Menangani like pada komentar
    - Mendukung sorting (terbaru, popular)
    
    CRUD OPERATIONS:
    - Create: Pengguna menulis komentar baru
    - Read: Menampilkan komentar di bawah post
    - Update: Pengguna mengedit komentar mereka
    - Delete: Pengguna/admin menghapus komentar
    
    RELASI EKSTERNAL:
    - User (pembuat komentar)
    - Post (postingan yang dikomentari) [di app post]
    - Report (laporan pada komentar) [di app report]
    """
    
    # Fields
    post = models.ForeignKey(
        'post.Post',  # Import dari app post
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Postingan"
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Pengguna"
    )
    
    content = models.TextField(
        max_length=1000,
        verbose_name="Isi Komentar",
        help_text="Komentar dapat berisi teks atau emoji (maksimal 1000 karakter)"
    )
    
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name="Komentar Induk",
        help_text="Komentar ini adalah balasan untuk komentar lain"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Dibuat Pada"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Diupdate Pada"
    )
    
    likes = models.ManyToManyField(
        User,
        related_name='comment_likes',
        blank=True,
        verbose_name="Like Komentar"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif"
    )

    class Meta:
        """Konfigurasi metadata untuk model Comment"""
        db_table = 'comment_comments'
        ordering = ['-created_at']
        verbose_name = "Komentar"
        verbose_name_plural = "Komentar"
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['parent_comment']),
            models.Index(fields=['is_active']),
        ]

    def clean(self):
        """
        VALIDASI CUSTOM:
        - Memastikan konten komentar tidak kosong
        - Validasi untuk reply comment (harus pada post yang sama)
        - Tidak boleh reply ke komentar yang sudah dihapus
        """
        super().clean()
        
        # Validasi konten
        if not self.content.strip():
            raise ValidationError({
                'content': 'Komentar tidak boleh kosong.'
            })
        
        # Validasi parent comment
        if self.parent_comment:
            if self.parent_comment.post != self.post:
                raise ValidationError({
                    'parent_comment': 'Reply comment harus pada post yang sama.'
                })
            
            if not self.parent_comment.is_active:
                raise ValidationError({
                    'parent_comment': 'Tidak bisa membalas komentar yang sudah dihapus.'
                })
            
            # Validasi depth (maksimal 2 level)
            if self.parent_comment.parent_comment:
                raise ValidationError({
                    'parent_comment': 'Hanya bisa membalas komentar utama, tidak bisa membalas balasan.'
                })

    def save(self, *args, **kwargs):
        """Override save method untuk menjalankan validasi custom"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        """Representasi string untuk Comment"""
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Komentar oleh {self.user.username}: {preview}"

    # Properties untuk analytics
    @property
    def total_likes(self):
        """Menghitung total like pada komentar"""
        return self.likes.count()

    @property
    def total_replies(self):
        """Menghitung total balasan komentar"""
        return self.replies.filter(is_active=True).count()

    @property
    def is_reply(self):
        """Cek apakah komentar ini adalah balasan"""
        return self.parent_comment is not None

    @property
    def depth_level(self):
        """Mendapatkan level kedalaman komentar (0 untuk utama, 1 untuk reply)"""
        return 1 if self.parent_comment else 0

    # Method untuk business logic
    def user_has_liked(self, user):
        """Cek apakah user tertentu sudah like komentar ini"""
        return self.likes.filter(id=user.id).exists() if user.is_authenticated else False

    def get_replies(self):
        """Mendapatkan semua balasan komentar yang aktif dan terurut"""
        return self.replies.filter(is_active=True).order_by('created_at')

    def soft_delete(self):
        """Soft delete komentar (menonaktifkan tanpa menghapus dari database)"""
        self.is_active = False
        self.save()
        
        # Juga soft delete semua replies
        self.replies.update(is_active=False)

    def restore(self):
        """Mengaktifkan kembali komentar yang di-soft delete"""
        self.is_active = True
        self.save()

    def can_edit(self, user):
        """Cek apakah user dapat mengedit komentar ini"""
        return user == self.user or user.is_staff

    def can_delete(self, user):
        """Cek apakah user dapat menghapus komentar ini"""
        return user == self.user or user.is_staff