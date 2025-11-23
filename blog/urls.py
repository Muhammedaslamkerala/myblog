from django.urls import path
from blog import views

app_name = 'blog'

urlpatterns = [
    # Static Pages
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('terms/', views.TermsView.as_view(), name='terms'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    
    # Post Display
    path('posts/', views.PostListView.as_view(), name='post_list'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_details'),
    path('category/<slug:slug>/', views.CategoryPostListView.as_view(), name='category'),
    path('tag/<slug:slug>/', views.TagPostListView.as_view(), name='tag_posts'),
    path('for-you/', views.ForYouPostListView.as_view(), name='for_you'),
    path('search/', views.SearchListView.as_view(), name='search'),
    
    # Dashboard and Post Management
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('my-posts/', views.MyPostsView.as_view(), name='my_posts'),
    path('write/', views.PostCreateView.as_view(), name='post_write'),
    path('post/<slug:slug>/edit/', views.PostEditView.as_view(), name='post_edit'),
    path('post/<slug:slug>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('api/auto-save/', views.AutoSaveView.as_view(), name='auto_save'),
    
    # Public Series Pages (accessible to everyone)
    path('series/', views.AllSeriesListView.as_view(), name='all_series_list'),
    path('series/<slug:slug>/', views.SeriesDetailView.as_view(), name='series_detail'),
    
    # User Dashboard - Series Management (author only)
    path('dashboard/series/', views.UserSeriesListView.as_view(), name='my_series_list'),
    path('dashboard/series/create/', views.SeriesCreateView.as_view(), name='my_series_create'),
    path('dashboard/series/<slug:slug>/edit/', views.SeriesUpdateView.as_view(), name='my_series_edit'),
    path('dashboard/series/<slug:slug>/manage/', views.SeriesManageView.as_view(), name='series_manage'),
    path('dashboard/series/<slug:slug>/delete/', views.SeriesDeleteView.as_view(), name='series_delete'),
    
    # Series AJAX Endpoints
    path('series/<slug:slug>/reorder/', views.SeriesReorderView.as_view(), name='series_reorder'),
    path('series/<slug:slug>/add-post/', views.SeriesAddPostView.as_view(), name='series_add_post'),
    path('series/<slug:slug>/remove-post/', views.SeriesRemovePostView.as_view(), name='series_remove_post'),
    
    # Reading List
    path('reading-list/', views.ReadingListView.as_view(), name='reading_list'),
    
    # AJAX Endpoints
    path('ajax/like/', views.toggle_like, name='toggle_like'),
    path('ajax/follow/', views.toggle_follow, name='toggle_follow'),
    path('ajax/reply/', views.submit_reply, name='submit_reply'),
    path('ajax/edit-comment/', views.edit_comment, name='edit_comment'),
    path('ajax/delete-comment/', views.delete_comment, name='delete_comment'),
    path('ajax/view/<slug:slug>/', views.increment_view_count, name='increment_view'),
    path('ajax/bookmark/', views.BookmarkToggleView.as_view(), name='bookmark_toggle'),

   
    # Ai
    path('api/chat/', views.chat_with_post, name='chat_with_post'),
]