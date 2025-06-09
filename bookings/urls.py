from django.urls import path
from . import views

urlpatterns = [
    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/room/<int:room_id>/', views.create_booking, name='create_booking'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('check-availability/', views.check_room_availability, name='check_availability'),
    path('booking/<int:booking_id>/review/add/', views.add_review, name='add_review'),
    path('booking/<int:booking_id>/review/edit/', views.edit_review, name='edit_review'),

    #payment
    path('bookings/<int:booking_id>/payment/', views.process_payment, name='process_payment'),
    path('bookings/<int:booking_id>/payment/history/', views.payment_history, name='payment_history'),
    path('bookings/<int:booking_id>/refund/', views.process_refund, name='process_refund'),
]