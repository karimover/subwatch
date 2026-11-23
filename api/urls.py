from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, SubscriptionCategoryViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="api-subscription")
router.register("payments", PaymentViewSet, basename="api-payment")
router.register("categories", SubscriptionCategoryViewSet, basename="api-category")

urlpatterns = router.urls
