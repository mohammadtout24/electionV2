from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from django.utils import timezone
from datetime import datetime
from django.contrib.auth import get_user_model # Import get_user_model for CustomUser reference

from .models import Candidate, Vote # The UserProfile model is implicitly available via the User model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
# Removed: from django.contrib.auth.models import User 

# --- Voting deadline: inclusive until 2025-11-01 23:59:59 ---
DEADLINE_NAIVE = datetime(2025, 11, 1, 23, 59, 59)

def get_aware_deadline():
    tz = timezone.get_current_timezone()
    return timezone.make_aware(DEADLINE_NAIVE, timezone=tz)


def submit_vote(request):
    if request.method == 'POST':
        user = request.user if request.user.is_authenticated else None

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        candidate_id = request.POST.get('vote')
        candidate = get_object_or_404(Candidate, id=candidate_id)

        deadline = get_aware_deadline()
        if timezone.now() > deadline:
            messages.error(request, "انتهت فترة التصويت.")
            return redirect('home')

        # Handle logged in users
        if user and user.is_authenticated: # Explicitly check for is_authenticated again just in case
            # We use update_or_create to allow users to change their vote
            vote_obj, created = Vote.objects.update_or_create(
                user=user,
                defaults={'candidate': candidate, 'session_key': session_key}
            )
        else:
            # Anonymous vote (by session)
            vote_obj, created = Vote.objects.update_or_create(
                session_key=session_key,
                defaults={'candidate': candidate}
            )
            # Store the name in session for anonymous users to show 'voted for' message (optional but consistent)
            request.session['voted_for'] = candidate.name


        if created:
            messages.success(request, f"تم تسجيل صوتك لصالح {candidate.name}.")
        else:
            messages.success(request, f"تم تحديث صوتك لصالح {candidate.name}.")

        return redirect('home')

    return redirect('home')



@login_required
def candidate_results(request):
    """Show results to candidates — only their own name/image and vote details, others hidden."""
    user = request.user

    # Ensure user is a candidate
    if not hasattr(user, 'candidate'):
        messages.error(request, "هذه الصفحة مخصصة للمرشحين فقط.")
        return redirect('home')

    # Get all candidates with vote counts
    candidates = Candidate.objects.annotate(vote_count=Count('votes')).order_by('-vote_count')
    total_votes = Vote.objects.count() or 1

    results = []
    for c in candidates:
        percentage = round((c.vote_count / total_votes) * 100, 1)

        results.append({
            'id': c.id,
            'is_self': c.user == user,
            'name': c.name if c.user == user else None,  # Only show name of logged-in candidate
            'image': c.image.url if (c.user == user and c.image) else None,  # Only show image for self
            'vote_count': c.vote_count,
            'percentage': percentage,
        })

    context = {
        'results': results,
        'total_votes': total_votes,
    }
    return render(request, 'candidates/candidate_results.html', context)



def home(request):
    """Main election page with voting or results depending on role."""
    # Ensure session key exists for anonymous voting/tracking
    if not request.session.session_key:
        request.session.create()

    user = request.user
    is_admin = user.is_authenticated and (user.is_staff or user.is_superuser) # Check authentication before staff/superuser
    is_candidate = user.is_authenticated and hasattr(user, 'candidate')

    has_voted = False
    voted_candidate_id = None
    voted_for_name = None 

    # Determine if the user/session has voted
    if user.is_authenticated:
        vote_obj = Vote.objects.filter(user=user).select_related('candidate').first()
        if vote_obj:
            has_voted = True
            voted_candidate_id = vote_obj.candidate.id
            voted_for_name = vote_obj.candidate.name
    else:
        # Anonymous user voting check
        session_key = request.session.session_key
        vote_obj = Vote.objects.filter(session_key=session_key, user__isnull=True).select_related('candidate').first()
        if vote_obj:
            has_voted = True
            voted_candidate_id = vote_obj.candidate.id
            voted_for_name = vote_obj.candidate.name


    deadline = get_aware_deadline()
    now = timezone.now()
    voting_closed = now > deadline

    # 1. Annotate candidates with vote counts
    candidates_with_counts = Candidate.objects.annotate(vote_count=Count('votes')).order_by('name')
    total_votes = Vote.objects.count()

    candidates_data = []

    # 2. Prepare context data (Crucial Fix for Admin Results)
    # The structure depends on whether the user is an admin or a regular voter
    if is_admin:
        # Admin gets full results with counts and percentages
        safe_total_votes = total_votes if total_votes > 0 else 1
        
        for c in candidates_with_counts:
            percentage = round((c.vote_count / safe_total_votes) * 100, 1)
            candidates_data.append({
                'candidate': c,
                'vote_count': c.vote_count,
                'vote_percentage': percentage,
            })
    else:
        # Regular users only need the candidate object for voting form
        candidates_data = [{'candidate': c} for c in candidates_with_counts]
        
    context = {
        'candidates_with_votes': candidates_data,
        'total_votes': total_votes,
        'has_voted': has_voted,
        'is_admin': is_admin,
        'is_candidate': is_candidate,
        'voted_for_name': voted_for_name, # Use the determined name
        'voted_candidate_id': voted_candidate_id,
        'voting_closed': voting_closed,
        'deadline': deadline.date(),
    }

    return render(request, 'candidates/home.html', context)


@login_required
def candidate_detail(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id)
    return render(request, 'candidates/candidate_detail.html', {'candidate': candidate})


def login_view(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"مرحبًا بعودتك، {user.username}!")

            # Both candidates and regular users go to home after login
            return redirect('home')
        else:
            messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")

    return render(request, 'candidates/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "تم تسجيل خروجك بنجاح.")
    return redirect('login')


@login_required
def all_users_list(request):
    # Only candidates can access this page
    if not hasattr(request.user, 'candidate'):
        messages.error(request, "غير مصرح لك بالوصول إلى هذه الصفحة.")
        return redirect('home')

    # Get the CustomUser model (which is the default User model in this project)
    CustomUser = get_user_model()
    
    # Fetch all User objects. We use select_related('userprofile') to efficiently 
    # fetch the phone_number data (from the UserProfile table) in the same query.
    # We also prefetch_related('candidate') to check if the user is a candidate easily.
    # Note: userprofile must be a OneToOneField from CustomUser.
    all_users = CustomUser.objects.filter(is_superuser=False).select_related('userprofile').prefetch_related('candidate').order_by('username')
    
    context = {
        'all_users': all_users, 
        'is_candidate': True,
    }
    
    return render(request, 'candidates/all_users.html', context)