import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import ForumPost
from .forms import ForumPostForm
from django.db import models
from django.contrib.auth.models import User

class PostListView(ListView):
    """
    View untuk menampilkan daftar semua post di homepage.
    Mendukung pagination dan filtering dasar.
    """
    model = ForumPost
    template_name = 'post/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    ordering = ['-created_at']

    def get_queryset(self):
        """Mengambil queryset dengan filter untuk post yang tidak dihapus"""
        queryset = super().get_queryset().filter(is_deleted=False)
        
        # Filter berdasarkan pencarian
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(author__username__icontains=search_query)
            )
        
        # Filter berdasarkan author
        author_filter = self.request.GET.get('author')
        if author_filter:
            queryset = queryset.filter(author__username=author_filter)
            
        return queryset

    def get_context_data(self, **kwargs):
        """Menambahkan context tambahan untuk template"""
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Forum Padel - Beranda'
        context['search_query'] = self.request.GET.get('search', '')
        return context


class PostDetailView(DetailView):
    """
    View untuk menampilkan detail lengkap sebuah post.
    Termasuk komentar dan interaksi.
    """
    model = ForumPost
    template_name = 'post/post_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        """Hanya tampilkan post yang tidak dihapus"""
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        """Menambahkan context untuk komentar dan interaksi"""
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # Menambahkan data komentar (asumsi model Comment ada)
        context['comments'] = post.comments.all().order_by('-created_at')
        context['total_comments'] = post.comments.count()
        
        # Status interaksi user saat ini
        if self.request.user.is_authenticated:
            # Asumsi ada model UserPostInteraction untuk tracking like/dislike per user
            try:
                user_interaction = UserPostInteraction.objects.get(
                    user=self.request.user, 
                    post=post
                )
                context['user_liked'] = user_interaction.liked
                context['user_disliked'] = user_interaction.disliked
            except UserPostInteraction.DoesNotExist:
                context['user_liked'] = False
                context['user_disliked'] = False
        
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """
    View untuk membuat post baru.
    Hanya bisa diakses oleh user yang sudah login.
    """
    model = ForumPost
    form_class = ForumPostForm
    template_name = 'post/post_form.html'
    success_url = reverse_lazy('post:post-list')

    def form_valid(self, form):
        """Set author sebagai user yang sedang login"""
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Buat Post Baru'
        context['submit_text'] = 'Publikasikan Post'
        return context


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View untuk mengupdate post yang sudah ada.
    Hanya author yang bisa mengedit post miliknya.
    """
    model = ForumPost
    form_class = ForumPostForm
    template_name = 'post/post_form.html'
    
    def test_func(self):
        """Cek apakah user adalah author dari post"""
        post = self.get_object()
        return self.request.user == post.author

    def get_success_url(self):
        """Redirect ke detail post setelah update"""
        return reverse_lazy('post:post-detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit Post'
        context['submit_text'] = 'Update Post'
        return context


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View untuk menghapus post (soft delete).
    Bisa diakses oleh author atau admin.
    """
    model = ForumPost
    template_name = 'post/post_confirm_delete.html'
    success_url = reverse_lazy('post:post-list')

    def test_func(self):
        """Cek apakah user adalah author atau admin"""
        post = self.get_object()
        return self.request.user == post.author or self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        """Soft delete dengan mengubah status is_deleted"""
        self.object = self.get_object()
        self.object.soft_delete()
        return redirect(self.success_url)


# AJAX Views untuk handle interaksi
class LikePostView(LoginRequiredMixin, View):
    """
    AJAX view untuk like post.
    Hanya menerima request POST.
    """
    def post(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk, is_deleted=False)
        
        # Asumsi ada model UserPostInteraction untuk tracking
        user_interaction, created = UserPostInteraction.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        response_data = {}
        
        if user_interaction.liked:
            # Jika sudah like, maka unlike
            post.decrement_likes()
            user_interaction.liked = False
            response_data['action'] = 'unliked'
        else:
            # Jika belum like, maka like
            post.increment_likes()
            user_interaction.liked = True
            
            # Jika sebelumnya dislike, hapus dislike
            if user_interaction.disliked:
                post.decrement_dislikes()
                user_interaction.disliked = False
            
            response_data['action'] = 'liked'
        
        user_interaction.save()
        
        response_data.update({
            'likes_count': post.likes_count,
            'dislikes_count': post.dislikes_count,
            'success': True
        })
        
        return JsonResponse(response_data)


class DislikePostView(LoginRequiredMixin, View):
    """
    AJAX view untuk dislike post.
    Hanya menerima request POST.
    """
    def post(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk, is_deleted=False)
        
        user_interaction, created = UserPostInteraction.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        response_data = {}
        
        if user_interaction.disliked:
            # Jika sudah dislike, maka undislike
            post.decrement_dislikes()
            user_interaction.disliked = False
            response_data['action'] = 'undisliked'
        else:
            # Jika belum dislike, maka dislike
            post.increment_dislikes()
            user_interaction.disliked = True
            
            # Jika sebelumnya like, hapus like
            if user_interaction.liked:
                post.decrement_likes()
                user_interaction.liked = False
            
            response_data['action'] = 'disliked'
        
        user_interaction.save()
        
        response_data.update({
            'likes_count': post.likes_count,
            'dislikes_count': post.dislikes_count,
            'success': True
        })
        
        return JsonResponse(response_data)


class SharePostView(View):
    """
    AJAX view untuk increment share count.
    Bisa diakses tanpa login.
    """
    def post(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk, is_deleted=False)
        post.increment_shares()
        
        return JsonResponse({
            'shares_count': post.shares_count,
            'success': True
        })


class GetPostStatsView(View):
    """
    AJAX view untuk mendapatkan statistik post.
    Berguna untuk update real-time.
    """
    def get(self, request, pk):
        post = get_object_or_404(ForumPost, pk=pk, is_deleted=False)
        
        return JsonResponse({
            'likes_count': post.likes_count,
            'dislikes_count': post.dislikes_count,
            'shares_count': post.shares_count,
            'total_comments': post.comments.count(),
            'success': True
        })


class PopularPostsView(ListView):
    """
    View untuk menampilkan post popular berdasarkan interaksi.
    """
    model = ForumPost
    template_name = 'post/popular_posts.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        """Mengambil post dengan interaksi tertinggi"""
        return ForumPost.objects.filter(is_deleted=False).annotate(
            total_interactions=Count('likes_count') + Count('dislikes_count') + Count('shares_count')
        ).order_by('-total_interactions', '-created_at')


# Model tambahan untuk tracking interaksi user (harus didefinisikan di models.py)
class UserPostInteraction(models.Model):
    """
    Model untuk melacak interaksi user dengan post (like/dislike).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE)
    liked = models.BooleanField(default=False)
    disliked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'post']