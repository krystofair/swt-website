"""URLs patterns, app specific"""

from django.urls import path, include, re_path

from . import views


urlpatterns = [
    path('kasbeer/login/', views.login, name='kasbeerLogin'),
    path('kasbeer/logout/', views.logout, name='kasbeerLogout'),
    path('kasbeer/order/', views.OrderCreation.as_view(), name='order'),
    path('kasbeer/order/<str:action>', views.OrderCreation.as_view(), name='orderAction'),
    path('kasbeer/orders/', views.list_orders, name='orders'),
    path('kasbeer/results/<int:order_id>/', views.order_result_view, name='orderResult'),
]