from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='first_sort'),
    path('original', views.sort_by_origins, name='originality'),
    path('brands', views.sort_by_origins, name='brands'),
    path('selected', views.sort_by_selected_brand, name='selected_brand'),
]
