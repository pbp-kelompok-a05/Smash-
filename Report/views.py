# report/views.py
import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Report
from post.models import Post
from comment.models import Comment

User = get_user_model()

class ReportAPIView(View):
    """
    API View untuk handling CRUD operations pada Report.
    Hanya superuser yang dapat mengakses semua reports.
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def check_superuser_permission(self, user):
        """Helper method untuk check superuser permissions"""
        return user.is_superuser or user.has_perm('report.manage_all_reports')

    def get(self, request, report_id=None):
        """
        GET: Retrieve reports (hanya untuk superuser)
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=401)
            
            if not self.check_superuser_permission(request.user):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Hanya admin yang dapat mengakses laporan'
                }, status=403)
            
            if report_id:
                # Get single report
                report = Report.objects.get(id=report_id)
                
                report_data = {
                    'id': report.id,
                    'reporter': report.reporter.username,
                    'reporter_id': report.reporter.id,
                    'category': report.category,
                    'category_display': report.get_category_display(),
                    'description': report.description,
                    'status': report.status,
                    'status_display': report.get_status_display(),
                    'created_at': report.created_at.isoformat(),
                    'reviewed_at': report.reviewed_at.isoformat() if report.reviewed_at else None,
                    'reviewed_by': report.reviewed_by.username if report.reviewed_by else None,
                    'content_type': None,
                    'content_data': None
                }
                
                # Include content data berdasarkan type
                if report.post:
                    report_data['content_type'] = 'post'
                    report_data['content_data'] = {
                        'id': report.post.id,
                        'title': report.post.title,
                        'content_preview': report.post.content[:100] + '...',
                        'user': report.post.user.username
                    }
                elif report.comment:
                    report_data['content_type'] = 'comment'
                    report_data['content_data'] = {
                        'id': report.comment.id,
                        'content': report.comment.content,
                        'user': report.comment.user.username,
                        'post_id': report.comment.post.id,
                        'post_title': report.comment.post.title
                    }
                
                return JsonResponse({
                    'status': 'success',
                    'report': report_data
                })
            
            else:
                # Get list of reports dengan filtering
                status_filter = request.GET.get('status', '')
                category_filter = request.GET.get('category', '')
                
                reports = Report.objects.all()
                
                # Apply filters
                if status_filter:
                    reports = reports.filter(status=status_filter)
                if category_filter:
                    reports = reports.filter(category=category_filter)
                
                # Pagination
                page = int(request.GET.get('page', 1))
                per_page = int(request.GET.get('per_page', 20))
                start = (page - 1) * per_page
                end = start + per_page
                
                reports_data = []
                for report in reports.order_by('-created_at')[start:end]:
                    report_info = {
                        'id': report.id,
                        'reporter': report.reporter.username,
                        'category': report.get_category_display(),
                        'status': report.get_status_display(),
                        'created_at': report.created_at.isoformat(),
                        'has_post': bool(report.post),
                        'has_comment': bool(report.comment)
                    }
                    
                    # Include content preview
                    if report.post:
                        report_info['content_preview'] = f"Post: {report.post.title}"
                    elif report.comment:
                        report_info['content_preview'] = f"Komentar: {report.comment.content[:50]}..."
                    
                    reports_data.append(report_info)
                
                return JsonResponse({
                    'status': 'success',
                    'reports': reports_data,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': reports.count(),
                        'has_next': end < reports.count()
                    },
                    'filters': {
                        'status': status_filter,
                        'category': category_filter
                    }
                })
                
        except Report.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Laporan tidak ditemukan'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error retrieving reports: {str(e)}'
            }, status=500)

    @method_decorator(require_http_methods(["POST"]))
    def post(self, request):
        """
        POST: Create new report
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=401)
            
            data = json.loads(request.body)
            
            # Validasi required fields
            required_fields = ['category']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Field {field} harus diisi'
                    }, status=400)
            
            # Validasi: harus ada post_id ATAU comment_id
            post_id = data.get('post_id')
            comment_id = data.get('comment_id')
            
            if not post_id and not comment_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Harus melaporkan post atau komentar'
                }, status=400)
            
            # Build report data
            report_data = {
                'reporter': request.user,
                'category': data['category'],
                'description': data.get('description', '')
            }
            
            # Link ke post atau comment
            if post_id:
                try:
                    report_data['post'] = Post.objects.get(id=post_id, is_deleted=False)
                except Post.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Post tidak ditemukan'
                    }, status=404)
            
            if comment_id:
                try:
                    report_data['comment'] = Comment.objects.get(id=comment_id, is_deleted=False)
                except Comment.DoesNotExist:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Komentar tidak ditemukan'
                    }, status=404)
            
            # Create report
            report = Report.objects.create(**report_data)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Laporan berhasil dikirim',
                'report_id': report.id
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON format'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error creating report: {str(e)}'
            }, status=500)

    @method_decorator(require_http_methods(["PUT"]))
    def put(self, request, report_id):
        """
        PUT: Update report status (hanya untuk superuser)
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=401)
            
            if not self.check_superuser_permission(request.user):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Hanya admin yang dapat mengupdate laporan'
                }, status=403)
            
            report = Report.objects.get(id=report_id)
            data = json.loads(request.body)
            
            # Update status
            if 'status' in data:
                report.status = data['status']
                if data['status'] == 'REVIEWED' and not report.reviewed_at:
                    report.reviewed_at = timezone.now()
                    report.reviewed_by = request.user
            
            report.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Status laporan berhasil diupdate',
                'report_id': report.id,
                'new_status': report.get_status_display()
            })
            
        except Report.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Laporan tidak ditemukan'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error updating report: {str(e)}'
            }, status=500)

    @method_decorator(require_http_methods(["DELETE"]))
    def delete(self, request, report_id):
        """
        DELETE: Delete report (hanya untuk superuser)
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=401)
            
            if not self.check_superuser_permission(request.user):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Hanya admin yang dapat menghapus laporan'
                }, status=403)
            
            report = Report.objects.get(id=report_id)
            report.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Laporan berhasil dihapus'
            })
            
        except Report.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Laporan tidak ditemukan'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error deleting report: {str(e)}'
            }, status=500)


class ReportStatsView(View):
    """
    View untuk mendapatkan statistics reports (hanya superuser)
    """
    
    def get(self, request):
        """
        GET: Get report statistics
        AJAX Support: ✅
        """
        try:
            if not request.user.is_authenticated or not self.check_superuser_permission(request.user):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Hanya admin yang dapat mengakses statistik'
                }, status=403)
            
            # Calculate statistics
            total_reports = Report.objects.count()
            pending_reports = Report.objects.filter(status='PENDING').count()
            reviewed_reports = Report.objects.filter(status='REVIEWED').count()
            resolved_reports = Report.objects.filter(status='RESOLVED').count()
            
            # Category statistics
            category_stats = {}
            for category in Report.REPORT_CATEGORIES:
                category_code = category[0]
                category_stats[category_code] = {
                    'name': category[1],
                    'count': Report.objects.filter(category=category_code).count()
                }
            
            # Recent activity
            recent_reports = Report.objects.order_by('-created_at')[:5]
            recent_data = []
            for report in recent_reports:
                recent_data.append({
                    'id': report.id,
                    'category': report.get_category_display(),
                    'status': report.get_status_display(),
                    'created_at': report.created_at.isoformat()
                })
            
            return JsonResponse({
                'status': 'success',
                'statistics': {
                    'total': total_reports,
                    'pending': pending_reports,
                    'reviewed': reviewed_reports,
                    'resolved': resolved_reports,
                    'categories': category_stats
                },
                'recent_activity': recent_data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error retrieving statistics: {str(e)}'
            }, status=500)