from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from django.utils import timezone
from datetime import datetime
from django.contrib.auth import get_user_model
from .models import Candidate, Vote
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm

# --- Voting deadline: inclusive until 2025-11-01 23:59:59 ---
DEADLINE_NAIVE = datetime(2025, 11, 7 , 23, 59, 59)

def get_aware_deadline():
    tz = timezone.get_current_timezone()
    return timezone.make_aware(DEADLINE_NAIVE, timezone=tz)


def submit_vote(request):
    if request.method == 'POST':
        user = request.user if request.user.is_authenticated else None

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        # 🚨 FIX APPLIED HERE: The HTML uses 'selected_candidate' for the radio buttons.
        candidate_id = request.POST.get('selected_candidate')
        
        # Add a safeguard against missing data, though 'required' in HTML should handle this.
        if not candidate_id:
            messages.error(request, "الرجاء اختيار مرشح قبل التصويت.")
            return redirect('home')
            
        # This will now successfully retrieve the candidate object using the correct key.
        candidate = get_object_or_404(Candidate, id=candidate_id)

        deadline = get_aware_deadline()
        if timezone.now() > deadline:
            messages.error(request, "انتهت فترة التصويت.")
            return redirect('home')

        # Handle logged in users
        if user and user.is_authenticated:
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

    if not hasattr(user, 'candidate'):
        messages.error(request, "هذه الصفحة مخصصة للمرشحين فقط.")
        return redirect('home')

    candidates = Candidate.objects.annotate(vote_count=Count('votes')).order_by('-vote_count')
    total_votes = Vote.objects.count() or 1

    results = []
    for c in candidates:
        percentage = round((c.vote_count / total_votes) * 100, 1)

        results.append({
            'id': c.id,
            'is_self': c.user == user,
            'name': c.name if c.user == user else None,
            'image': c.image.url if (c.user == user and c.image) else None,
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
    if not request.session.session_key:
        request.session.create()

    user = request.user
    is_admin = user.is_authenticated and (user.is_staff or user.is_superuser)
    is_candidate = user.is_authenticated and hasattr(user, 'candidate')

    has_voted = False
    voted_candidate_id = None
    voted_for_name = None 

    # Determine if the user/session has voted (logic unchanged)
    if user.is_authenticated:
        vote_obj = Vote.objects.filter(user=user).select_related('candidate').first()
        if vote_obj:
            has_voted = True
            voted_candidate_id = vote_obj.candidate.id
            voted_for_name = vote_obj.candidate.name
    else:
        session_key = request.session.session_key
        vote_obj = Vote.objects.filter(session_key=session_key, user__isnull=True).select_related('candidate').first()
        if vote_obj:
            has_voted = True
            voted_candidate_id = vote_obj.candidate.id
            voted_for_name = vote_obj.candidate.name


    deadline = get_aware_deadline()
    now = timezone.now()
    voting_closed = now > deadline

    # --- CONDITIONAL SORTING LOGIC ---
    candidates_queryset = Candidate.objects.annotate(vote_count=Count('votes'))
    
    if is_admin:
        # Admin: Sort by votes (descending), then by name
        candidates_with_counts = candidates_queryset.order_by('-vote_count', 'name')
    else:
        # Voter/Candidate: Sort strictly by name (alphabetical, ascending)
        candidates_with_counts = candidates_queryset.order_by('name')
        
    total_votes = Vote.objects.count()

    candidates_data = []
    max_votes = 1 # Initialize max_votes for progress bar calculation

    # 2. Prepare context data
    if is_admin:
        # Admin view: Calculate max_votes and build detailed results data
        safe_total_votes = total_votes if total_votes > 0 else 1
        
        if candidates_with_counts:
            # Since the queryset is sorted by vote_count descending, the max is the first item's count
            max_votes = candidates_with_counts.first().vote_count
            max_votes = max_votes if max_votes > 0 else 1 # Ensure no division by zero
        
        for c in candidates_with_counts:
            percentage = round((c.vote_count / safe_total_votes) * 100, 1)
            candidates_data.append({
                'candidate': c,
                'vote_count': c.vote_count,
                'vote_percentage': percentage,
            })
    else:
        # Voter view: Just pass candidate objects
        candidates_data = [{'candidate': c} for c in candidates_with_counts]
        
    context = {
        'candidates_with_votes': candidates_data,
        'total_votes': total_votes,
        'max_votes': max_votes,
        'has_voted': has_voted,
        'is_admin': is_admin,
        'is_candidate': is_candidate,
        'voted_for_name': voted_for_name,
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
    if not hasattr(request.user, 'candidate'):
        messages.error(request, "غير مصرح لك بالوصول إلى هذه الصفحة.")
        return redirect('home')

    CustomUser = get_user_model()
    
    all_users = CustomUser.objects.filter(is_superuser=False).select_related('userprofile').prefetch_related('candidate').order_by('username')
    
    context = {
        'all_users': all_users, 
        'is_candidate': True,
    }
    
    return render(request, 'candidates/all_users.html', context)
