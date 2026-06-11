from django.urls import path
from . import views
from . import staff_views
from . import api_views

urlpatterns = [
    #public views
    path('', views.hotel_list, name='home'), 
    path('hotels/', views.hotel_list, name='hotel_list'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    path('recommendations/', views.hotel_recommendations, name='hotel_recommendations'),
    path('search/', views.search_hotels, name='search_hotels'),
    path('favorite/toggle/<int:hotel_id>/', views.toggle_favorite, name='toggle_favorite'),    path('favorites/', views.favorite_list, name='favorites'),
    path('api/hotels/map-data/', api_views.hotel_map_data, name='hotel_map_data'),
    
    #staff views
    path('staff/', staff_views.staff_dashboard, name='staff_dashboard'),
    path('staff/hotels/', staff_views.HotelListView.as_view(), name='staff_hotel_list'),
    path('staff/hotels/add/', staff_views.create_hotel, name='staff_hotel_add'),
    path('staff/hotels/import/', staff_views.import_hotels, name='staff_hotel_import'),
    path('staff/hotels/<int:pk>/', staff_views.hotel_detail, name='staff_hotel_detail'),
    path('staff/hotels/<int:pk>/edit/', staff_views.update_hotel, name='staff_hotel_edit'),
    path('staff/hotels/<int:pk>/delete/', staff_views.HotelDeleteView.as_view(), name='staff_hotel_delete'),
    path('staff/hotels/<int:pk>/update-coordinates/', staff_views.update_coordinates, name='update_coordinates'),
]