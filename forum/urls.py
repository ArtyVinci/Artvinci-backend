from django.urls import path
from . import views

app_name = 'forum'

urlpatterns = [
    path('categories/', views.CategoryListCreateView.as_view(), name='categories'),
    path('topics/', views.TopicListCreateView.as_view(), name='topics'),
    path('topics/<str:topic_id>/', views.TopicDetailView.as_view(), name='topic-detail'),
    path('topics/<str:topic_id>/replies/', views.ReplyListCreateView.as_view(), name='topic-replies'),
    path('topics/<str:topic_id>/suggest-reply/', views.SuggestReplyView.as_view(), name='topic-suggest-reply'),
    path('replies/<str:reply_id>/', views.ReplyDetailView.as_view(), name='reply-detail'),
    path('topics/<str:topic_id>/helpful/', views.TopicHelpfulView.as_view(), name='topic-helpful'),
    path('replies/<str:reply_id>/helpful/', views.ReplyHelpfulView.as_view(), name='reply-helpful'),
]
