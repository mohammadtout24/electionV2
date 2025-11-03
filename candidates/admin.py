from django.contrib import admin
# CRITICAL: Import the Vote model
from .models import Candidate,UserProfile, Vote

# Register the models already present
admin.site.register(Candidate)
admin.site.register(UserProfile)

# ✅ ADD THIS: Register the Vote model
@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    # Display the linked user, the candidate they voted for, and the timestamp
    list_display = ('id', 'user_link', 'candidate', 'voted_at')
    # Allow filtering by candidate (project)
    list_filter = ('candidate',)
    # Allow searching by user's username or candidate's name
    search_fields = ('user__username', 'candidate__name')
    # Use raw_id_fields for foreign keys if you have many users/candidates
    raw_id_fields = ('user', 'candidate')
    
    # Custom method to display the username/ID as a link
    def user_link(self, obj):
        # If a user is linked (logged-in vote), show their username
        if obj.user:
            return obj.user.username
        # If no user is linked (anonymous vote), show 'Anonymous'
        return "Anonymous (Session Key)"
    user_link.short_description = 'Voter'

    # Hide the session key from regular list view but keep it for detail
    # fields = ('user', 'candidate', 'voted_at', 'session_key') 
    
    # Optional: Display votes in descending order of time
    ordering = ('-voted_at',)
