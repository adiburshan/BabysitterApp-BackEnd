from django.urls import include, path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView , TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
# add the full crud's paths

router.register('babysitter/availability', views.AvailableTimeActions, basename='babysitter-availability')
router.register('reviews', views.ReviewsViewSet, basename='reviews')


urlpatterns = [
    # User
    path("login/", views.MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register),
    path('user-delete/', views.deactivate_my_user),
    path('admin-user-delete/', views.admin_deactivate_user),
    # My profile
    path('babysitter-profile/me/', views.BabysitterMe.as_view()),
    path('parents-profile/me/', views.ParentMe.as_view()),
    # Babysitter 
    path('babysitters-list/', views.BabysitterListView.as_view()),
    # Parents
    path('parents-list/' , views.ParentsListView.as_view()),
    # Kids
    path('kids-list/', views.KidsListView.as_view()), 
    path('kids-add/', views.KidsCreate.as_view()),
    path('kids-update/<int:pk>/', views.KidsActions.as_view()),
    # Available Time
    path('availability-list/', views.AvailableTimeListView.as_view()),
    # + availability/* CRUD (in the router)
    # Requests
    path('request-add/', views.RequestsViewSet.as_view()),
    path('requests-list/', views.ShowRequests.as_view()),
    path('request-update/<int:pk>/', views.RequestActionsForBabysitter.as_view()),
    path('request-delete/<int:pk>/', views.RequestDeactivate.as_view()),
    # Reviews
    path('reviews-list/', views.ShowReviews.as_view()),
    # + reviews/* CRUD (in the router)
    # Ai
    path('ai-time-request/', views.generate_ai_time_request),
    path('messages-count/', views.unread_messages_count),
    path('messages-read/', views.mark_ai_messages_read),
    # Meetings
    path('meetings-add/', views.CreateMeetingView.as_view()),
    path('meetings-list/', views.ShowMeetings.as_view()),
    path('meeting-update/<int:pk>/', views.MeetingActionsForBabysitter.as_view()),
    path('babysit-request-add/', views.BabysitRequestCreate.as_view()),
    path('meeting-actions/', views.MeetingActions.as_view()),
    # Router
    path('', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)