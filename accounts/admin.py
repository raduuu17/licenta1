from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserPreference

class UserPreferenceInline(admin.StackedInline):
    model = UserPreference
    can_delete = False
    verbose_name_plural = 'Preferences'

class CustomUserAdmin(UserAdmin):
    inlines = (UserPreferenceInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {'fields': ('phone_number', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Information', {'fields': ('phone_number', 'profile_picture')}),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_city', 'min_star_rating', 'prefer_pet_friendly', 'prefer_family_friendly')
    list_filter = ('wifi', 'parking', 'pool', 'spa', 'gym', 'prefer_pet_friendly', 'prefer_family_friendly')
    search_fields = ('user__username', 'preferred_city', 'preferred_district')