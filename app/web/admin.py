from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, ChatTicket, Mission


# Define an inline admin descriptor for User Profile model
# which acts a bit like a singleton
class ProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'user_profile'


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# missions on admin site
# def mark_hidden(modaladmin, request, queryset):
#     queryset.update(is_hidden=True)
#
#
# class MissionAdmin(admin.ModelAdmin):
#     list_display = ['date', 'name', 'unique_code', 'is_closed', 'is_hidden', ]
#     ordering = ['date']
#     actions = [mark_hidden]
#
#
# admin.site.register(Mission, MissionAdmin)
#
#
# # chat ticket on admin site
# class ChatTicketAdmin(admin.ModelAdmin):
#     list_display = ['user', 'ticket', ]
#
#
# admin.site.register(ChatTicket, ChatTicketAdmin)
