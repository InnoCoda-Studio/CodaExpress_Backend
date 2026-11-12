from django.urls import path
from .views import (
    CreateOrderView,
    CustomerOrderListView,
    AvailableOrdersListView,
    AcceptOrderView,
    UpdateOrderStatusView,
    OrderMessageListCreateView,
)

urlpatterns = [
    path('book/', CreateOrderView.as_view(), name='book-order'),
    path('customer/list/', CustomerOrderListView.as_view(), name='customer-orders'),
    path('available/', AvailableOrdersListView.as_view(), name='available-orders'),
    path('<int:pk>/accept/', AcceptOrderView.as_view(), name='accept-order'),
    path('<int:pk>/status/', UpdateOrderStatusView.as_view(), name='update-order-status'),
    path('<int:order_id>/messages/', OrderMessageListCreateView.as_view(), name='order-messages'),
]