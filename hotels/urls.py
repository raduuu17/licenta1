from django.urls import path
from . import views
from . import staff_views

urlpatterns = [
    #public views
    path('', views.hotel_list, name='home'), 
    path('hotels/', views.hotel_list, name='hotel_list'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    path('recommendations/', views.hotel_recommendations, name='hotel_recommendations'),
    path('search/', views.search_hotels, name='search_hotels'),

    #staff views
    path('staff/', staff_views.staff_dashboard, name='staff_dashboard'),
    path('staff/hotels/', staff_views.HotelListView.as_view(), name='staff_hotel_list'),
    path('staff/hotels/add/', staff_views.create_hotel, name='staff_hotel_add'),
    path('staff/hotels/<int:pk>/', staff_views.hotel_detail, name='staff_hotel_detail'),
    path('staff/hotels/<int:pk>/edit/', staff_views.update_hotel, name='staff_hotel_edit'),
    path('staff/hotels/<int:pk>/delete/', staff_views.HotelDeleteView.as_view(), name='staff_hotel_delete'),
]