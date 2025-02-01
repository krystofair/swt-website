"""
URL configuration for tutu project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.contrib import admin
from rest_framework import routers, serializers, viewsets
from kasbeer import views

class A(views.TemplateView):
    template_engine = 'jinja2'
    title = "Tworzenie orderu :O"

    def get(self, request, template_name, *args, **kwargs):
        template_name = template_name.rstrip('.html')
        self.template_name = f"/kasbeer/{template_name}.html"
        return super().get(request, *args, **kwargs)

urlpatterns = [
    # path('', include('dashboard.urls')),
    path('admin/', admin.site.urls),
    path('orders/create/', views.OrderCreation.as_view()),
    path('leagues/<str:country>/', views.leagues),
    path('test/kasbeer/<str:template_name>', A.as_view())
    #   path('orders/filters/', views.FilterView.as_view()),
    #   path('orders/select/', views.ChosenMatchesView.as_view()),
    #   path('orders/save/', views.OrderNewView.as_view()),  # method POST
    #   path('orders/create/', views.OrderCreation.as_view(orders.Order())
]
