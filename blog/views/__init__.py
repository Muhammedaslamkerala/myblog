# blog/views/__init__.py

from .post_views import (
    HomeView,
    PostListView,
    CategoryPostListView,
    PostDetailView,
    SearchListView,
    TagPostListView,
    ForYouPostListView
)

from .author_views import (
    PostCreateView,
    PostEditView,
    PostDeleteView,
    DashboardView,
    MyPostsView,
    AutoSaveView
)

from .ajax_views import *
   

from .static_views import (
    AboutView,
    ContactView,
    TermsView,
    PrivacyView
)

from .series_views import *

from .ai_views import *

