from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from .models import Cohort, GameMode, Fixture, TeamUPFixture, Round, RoundPlayerStats, TeamUPRound, TeamUPRoundStats, TeamUPPlayerRoundStats, GameStage, TeamUP, Notification, TeamUPInvite, MPesaTransaction, FreeAgent, SquadRecruitment, JoinRequest
from users.models import User
import requests
import json
import base64
from datetime import datetime
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from .ai_service import ai_service
import os
from dotenv import load_dotenv

load_dotenv()
def landing_page_view(request):
    return render(request, 'home/index.html')

@login_required
def dashboard_view(request):
    profile = getattr(request.user, 'profile', None)
    active_cohorts = Cohort.objects.filter(is_open_to_join=True).order_by('-start_date')
    game_modes = GameMode.objects.all()
    
    # Fetch fixtures (Showing both upcoming and played)
    now = timezone.now()
    solo_fixtures = Fixture.objects.filter(players=request.user, match_date__gte=now - timezone.timedelta(days=1)).order_by('match_date')[:10]
    team_fixtures = TeamUPFixture.objects.filter(teamups__players=request.user, match_date__gte=now - timezone.timedelta(days=1)).distinct().order_by('match_date')[:10]
    
    # Fetch results
    recent_solo_results = RoundPlayerStats.objects.filter(player=request.user).order_by('-round_instance__match_date')[:5]
    recent_team_results = TeamUPRoundStats.objects.filter(team__players=request.user).distinct().order_by('-round_instance__match_date')[:5]
    
    # Squad Management
    user_squads = request.user.teamups.all()
    pending_invites = TeamUPInvite.objects.filter(invitee=request.user, status='PENDING')
    
    # Squad Readiness for active cohorts
    squad_readiness = []
    for squad in user_squads:
        for cohort in active_cohorts:
            squad_readiness.append({
                'squad': squad,
                'cohort': cohort,
                'is_ready': squad.is_ready(cohort),
                'paid_count': sum(1 for p in squad.get_payment_status(cohort) if p['paid']),
                'total_needed': squad.game_mode.max_players
            })
    
    context = {
        'profile': profile,
        'active_cohorts': active_cohorts,
        'game_modes': game_modes,
        'solo_fixtures': solo_fixtures,
        'team_fixtures': team_fixtures,
        'recent_solo_results': recent_solo_results,
        'recent_team_results': recent_team_results,
        'user_squads': user_squads,
        'pending_invites': pending_invites,
        'squad_readiness': squad_readiness,
    }
    return render(request, 'home/dashboard.html', context)

def leaderboard_view(request):
    mode_id = request.GET.get('mode')
    cohort_id = request.GET.get('cohort')
    stage_id = request.GET.get('stage')
    q = request.GET.get('q', '')
    
    # Base queryset for users who have stats
    users_qs = User.objects.all()
    
    if q:
        users_qs = users_qs.filter(gamer_tag__icontains=q)
    
    # Define filters for annotations
    stats_filters = {}
    if mode_id:
        stats_filters['player_stats__round_instance__stage__game_mode_id'] = mode_id
    if cohort_id:
        stats_filters['player_stats__round_instance__cohort_id'] = cohort_id
    if stage_id:
        stats_filters['player_stats__round_instance__stage_id'] = stage_id
        
    # Aggregate stats per player
    leaderboard_data = users_qs.filter(player_stats__isnull=False).filter(**stats_filters).annotate(
        total_kills=Sum('player_stats__kills'),
        total_damage=Sum('player_stats__damage'),
        total_xp=Sum('player_stats__xp'),
        matches_played=Count('player_stats')
    ).select_related('profile').order_by('-total_xp', '-total_kills').distinct()
    
    context = {
        'leaderboard': leaderboard_data,
        'game_modes': GameMode.objects.all(),
        'cohorts': Cohort.objects.all(),
        'stages': GameStage.objects.all(),
        'selected_mode': mode_id,
        'selected_cohort': cohort_id,
        'selected_stage': stage_id,
        'q': q,
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'home/partials/leaderboard_results.html', context)
        
    return render(request, 'home/leaderboard.html', context)

@login_required
def join_cohort_view(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id)
    profile = getattr(request.user, 'profile', None)
    
    if not profile:
        # This shouldn't happen with the new registration flow, but good to be safe
        from users.models import PersonalProfile
        profile, created = PersonalProfile.objects.get_or_create(user=request.user)
    
    if cohort.is_open_to_join:
        if profile not in cohort.participants.all():
            cohort.participants.add(profile)
            messages.success(request, f"Successfully joined {cohort.name}!")
        else:
            messages.info(request, f"You are already a participant in {cohort.name}.")
    else:
        messages.error(request, f"Registration for {cohort.name} is currently closed.")
        
    return redirect('dashboard')

def player_analytics_view(request, gamer_tag):
    user = get_object_or_404(User, gamer_tag=gamer_tag)
    profile = getattr(user, 'profile', None)
    
    # Career Stats (Solo)
    solo_stats = RoundPlayerStats.objects.filter(player=user).aggregate(
        total_kills=Sum('kills'),
        total_damage=Sum('damage'),
        total_xp=Sum('xp'),
        matches_played=Count('id'),
        wins=Count('id', filter=Q(rank=1))
    )
    
    # Career Stats (Team) - combat stats from player's personal performance, context from team stats
    team_combat_stats = TeamUPPlayerRoundStats.objects.filter(player=user).aggregate(
        total_kills=Sum('kills'),
        total_damage=Sum('damage'),
        total_xp=Sum('xp'),
    )
    
    team_context_stats = TeamUPRoundStats.objects.filter(team__players=user).aggregate(
        matches_played=Count('id'),
        wins=Count('id', filter=Q(rank=1))
    )
    
    team_stats = {**team_combat_stats, **team_context_stats}
    
    # Recent History
    from django.db.models import OuterRef, Subquery
    
    team_rank_subquery = TeamUPRoundStats.objects.filter(
        round_instance=OuterRef('round_instance'),
        team=OuterRef('team')
    ).values('rank')[:1]

    recent_solo = RoundPlayerStats.objects.filter(player=user).select_related('round_instance__stage').order_by('-round_instance__match_date')[:10]
    recent_team = TeamUPPlayerRoundStats.objects.filter(player=user).select_related('team', 'round_instance__stage').annotate(
        team_rank=Subquery(team_rank_subquery)
    ).order_by('-round_instance__match_date')[:10]
    
    # Teams
    teams = user.teamups.all()
    
    context = {
        'player': user,
        'profile': profile,
        'solo_stats': solo_stats,
        'team_stats': team_stats,
        'recent_solo': recent_solo,
        'recent_team': recent_team,
        'teams': teams,
    }
    return render(request, 'home/analytics.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_dashboard_view(request):
    all_cohorts = Cohort.objects.all().order_by('-start_date')
    selected_cohort_id = request.GET.get('cohort_id')
    
    if selected_cohort_id:
        selected_cohort = get_object_or_404(Cohort, id=selected_cohort_id)
    else:
        selected_cohort = all_cohorts.first()
    
    # Aggregated Stats
    stats = {
        'total_players': selected_cohort.participants.count() if selected_cohort else 0,
        'total_teams': selected_cohort.teamups.count() if selected_cohort else 0,
    }
    
    if selected_cohort:
        # Performance sums
        solo_performance = RoundPlayerStats.objects.filter(round_instance__cohort=selected_cohort).aggregate(
            kills=Sum('kills'),
            damage=Sum('damage'),
            xp=Sum('xp')
        )
        team_performance = TeamUPRoundStats.objects.filter(round_instance__cohort=selected_cohort).aggregate(
            kills=Sum('kills'),
            damage=Sum('damage'),
            xp=Sum('xp')
        )
        
        stats['total_kills'] = (solo_performance['kills'] or 0) + (team_performance['kills'] or 0)
        stats['total_damage'] = (solo_performance['damage'] or 0) + (team_performance['damage'] or 0)
        stats['total_xp'] = (solo_performance['xp'] or 0) + (team_performance['xp'] or 0)
        
        # Lists
        recent_solo_results = RoundPlayerStats.objects.filter(round_instance__cohort=selected_cohort).order_by('-round_instance__match_date')[:10]
        recent_team_results = TeamUPRoundStats.objects.filter(round_instance__cohort=selected_cohort).order_by('-round_instance__match_date')[:10]
        
        # All Fixtures for the cohort
        all_solo_fixtures = Fixture.objects.filter(cohort=selected_cohort).order_by('match_date')[:50]
        all_team_fixtures = TeamUPFixture.objects.filter(cohort=selected_cohort).order_by('match_date')[:50]

        # Participants List
        participants = User.objects.filter(profile__cohort_participants=selected_cohort).annotate(
            cohort_kills=Sum('player_stats__kills', filter=Q(player_stats__round_instance__cohort=selected_cohort)),
            cohort_xp=Sum('player_stats__xp', filter=Q(player_stats__round_instance__cohort=selected_cohort))
        ).order_by('-cohort_xp')
    else:
        recent_solo_results = []
        recent_team_results = []
        all_solo_fixtures = []
        all_team_fixtures = []
        participants = []

    context = {
        'all_cohorts': all_cohorts,
        'selected_cohort': selected_cohort,
        'stats': stats,
        'recent_solo_results': recent_solo_results,
        'recent_team_results': recent_team_results,
        'all_solo_fixtures': all_solo_fixtures,
        'all_team_fixtures': all_team_fixtures,
        'participants': participants,
    }
    return render(request, 'home/admin_dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def record_team_stats_view(request, fixture_id):
    fixture = get_object_or_404(TeamUPFixture, id=fixture_id)
    
    # Get or create the Round instance
    round_instance, created = TeamUPRound.objects.get_or_create(
        fixture=fixture,
        defaults={
            'cohort': fixture.cohort,
            'stage': fixture.stage,
            'match_date': fixture.match_date,
        }
    )
    
    if created:
        for team in fixture.teamups.all():
            round_instance.teamup.add(team)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_team_rank':
            team_id = request.POST.get('team_id')
            team = get_object_or_404(TeamUP, id=team_id)
            rank = request.POST.get('rank') or 0
            
            TeamUPRoundStats.objects.update_or_create(
                round_instance=round_instance,
                team=team,
                defaults={'rank': rank}
            )
            messages.success(request, f"Rank updated for {team.name}")
            
        elif action == 'save_player_stats':
            player_id = request.POST.get('player_id')
            team_id = request.POST.get('team_id')
            player = get_object_or_404(User, id=player_id)
            team = get_object_or_404(TeamUP, id=team_id)
            
            player_stat, _ = TeamUPPlayerRoundStats.objects.update_or_create(
                round_instance=round_instance,
                team=team,
                player=player,
                defaults={
                    'kills': request.POST.get('kills') or 0,
                    'deaths': request.POST.get('deaths') or 0,
                    'damage': request.POST.get('damage') or 0,
                    'xp': request.POST.get('xp') or 0,
                }
            )
            
            # Re-aggregate team stats
            team_stats = TeamUPRoundStats.objects.filter(round_instance=round_instance, team=team).first()
            if team_stats:
                all_member_stats = TeamUPPlayerRoundStats.objects.filter(round_instance=round_instance, team=team).aggregate(
                    total_kills=Sum('kills'),
                    total_damage=Sum('damage'),
                    total_xp=Sum('xp'),
                    total_deaths=Sum('deaths')
                )
                team_stats.kills = all_member_stats['total_kills'] or 0
                team_stats.damage = all_member_stats['total_damage'] or 0
                team_stats.xp = all_member_stats['total_xp'] or 0
                team_stats.deaths = all_member_stats['total_deaths'] or 0
                team_stats.save()
                
            messages.success(request, f"Stats updated for {player.gamer_tag} ({team.name})")
            
            # Trigger notification for player
            Notification.objects.create(
                recipient=player,
                actor=request.user,
                message=f"Results recorded for your team match in {fixture.stage.name}.",
                notification_type='RESULT',
                link=f"/analytics/{player.gamer_tag}/"
            )

        return redirect('record_team_stats', fixture_id=fixture_id)

    # Context prep
    teams_data = []
    round_team_stats = {s.team.id: s for s in round_instance.team_stats.all()}
    
    # Hierarchical stats: {team_id: {player_id: stats_obj}}
    player_stats_map = {}
    for s in round_instance.player_team_stats.all():
        if s.team.id not in player_stats_map:
            player_stats_map[s.team.id] = {}
        player_stats_map[s.team.id][s.player.id] = s
    
    for team in fixture.teamups.all():
        teams_data.append({
            'team': team,
            'stat_summary': round_team_stats.get(team.id),
            'members': team.players.all(),
        })

    context = {
        'fixture': fixture,
        'round': round_instance,
        'teams_data': teams_data,
        'player_stats_map': player_stats_map,
    }
    return render(request, 'home/record_team_stats.html', context)

@user_passes_test(lambda u: u.is_staff)
def record_solo_stats_view(request, fixture_id):
    fixture = get_object_or_404(Fixture, id=fixture_id)
    
    # Get or create the Round instance
    round_instance, created = Round.objects.get_or_create(
        fixture=fixture,
        defaults={
            'cohort': fixture.cohort,
            'stage': fixture.stage,
            'match_date': fixture.match_date,
        }
    )
    
    # Ensure participants are synced (optional but good for data integrity)
    if created:
        for player in fixture.players.all():
            round_instance.participants.add(player)

    if request.method == 'POST':
        player_id = request.POST.get('player_id')
        player = get_object_or_404(User, id=player_id)
        
        try:
            RoundPlayerStats.objects.update_or_create(
                round_instance=round_instance,
                player=player,
                defaults={
                    'rank': request.POST.get('rank') or 0,
                    'kills': request.POST.get('kills') or 0,
                    'deaths': request.POST.get('deaths') or 0,
                    'damage': request.POST.get('damage') or 0,
                    'xp': request.POST.get('xp') or 0,
                    'time_alive': request.POST.get('time_alive', ''),
                }
            )
            messages.success(request, f"Stats updated for {player.gamer_tag}")
            
            # Trigger notification for player
            Notification.objects.create(
                recipient=player,
                actor=request.user,
                message=f"Your stats for {fixture.stage.name} have been updated.",
                notification_type='RESULT',
                link=f"/analytics/{player.gamer_tag}/"
            )
        except Exception as e:
            messages.error(request, f"Error updating stats: {str(e)}")
            
        return redirect('record_solo_stats', fixture_id=fixture_id)

    # Fetch recorded stats to show in table
    recorded_stats = {s.player.id: s for s in round_instance.teamup_stats.all()}
    
    context = {
        'fixture': fixture,
        'round': round_instance,
        'players': fixture.players.all(),
        'recorded_stats': recorded_stats,
    }
    return render(request, 'home/record_solo_stats.html', context)

# Squad Management Views
@login_required
def create_squad_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        mode_id = request.POST.get('game_mode')
        game_mode = get_object_or_404(GameMode, id=mode_id)
        
        team = TeamUP.objects.create(
            name=name,
            captain=request.user,
            game_mode=game_mode
        )
        team.players.add(request.user)
        
        messages.success(request, f"Squad '{name}' created successfully!")
        return redirect('manage_squad', team_id=team.id)
    
    game_modes = GameMode.objects.filter(name__in=['Team', 'Duo', 'Squad'])
    return render(request, 'home/create_squad.html', {'game_modes': game_modes})

@login_required
def manage_squad_view(request, team_id):
    team = get_object_or_404(TeamUP, id=team_id)
    if team.captain != request.user:
        messages.error(request, "Only the captain can manage this squad.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        gamer_tag = request.POST.get('gamer_tag')
        
        # Check squad capacity
        current_count = team.players.count()
        pending_count = team.invites.filter(status='PENDING').count()
        if (current_count + pending_count) >= team.game_mode.max_players:
            messages.error(request, f"Squad full. Capacity for {team.game_mode.name} is {team.game_mode.max_players} (including pending invites).")
        else:
            try:
                invitee = User.objects.get(gamer_tag__iexact=gamer_tag)
                if invitee in team.players.all():
                    messages.info(request, f"{gamer_tag} is already in the squad.")
                else:
                    invite, created = TeamUPInvite.objects.get_or_create(
                        inviter=request.user,
                        invitee=invitee,
                        team=team,
                        status='PENDING'
                    )
                    if created:
                        # Create notification for invitee
                        Notification.objects.create(
                            recipient=invitee,
                            actor=request.user,
                            message=f"{request.user.gamer_tag} invited you to join '{team.name}'.",
                            notification_type='INVITE',
                            link='/notifications/' # Or squad invites list
                        )
                        messages.success(request, f"Invite sent to {gamer_tag}!")
                    else:
                        messages.info(request, f"An invite is already pending for {gamer_tag}.")
            except User.DoesNotExist:
                messages.error(request, f"Operator with tag '{gamer_tag}' not found.")
        return redirect('manage_squad', team.id)
            
    active_cohorts = Cohort.objects.filter(is_open_to_join=True).order_by('-start_date')
    member_statuses = []
    for cohort in active_cohorts:
        member_statuses.append({
            'cohort': cohort,
            'statuses': team.get_payment_status(cohort)
        })

    invites = team.invites.filter(status='PENDING')
    context = {
        'team': team, 
        'invites': invites,
        'member_statuses': member_statuses,
        'active_cohorts': active_cohorts
    }
    return render(request, 'home/manage_squad.html', context)
            

def normalize_phone(phone):
    """Normalize phone number to 254XXXXXXXXX format."""
    phone = str(phone).strip()
    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('+'):
        phone = phone[1:]
    return phone

@login_required
def gamemode_detail_view(request, mode_id):
    mode = get_object_or_404(GameMode, id=mode_id)
    active_cohorts = Cohort.objects.filter(is_open_to_join=True).order_by('-start_date')
    
    # Fetch user squads for this mode if it's not Solo
    user_squads = None
    if mode.name != 'Solo':
        user_squads = TeamUP.objects.filter(players=request.user, game_mode=mode)
    
    context = {
        'mode': mode,
        'active_cohorts': active_cohorts,
        'user_squads': user_squads,
    }
    return render(request, 'home/gamemode_detail.html', context)

@login_required
def initiate_payment_view(request, mode_id, cohort_id):
    mode = get_object_or_404(GameMode, id=mode_id)
    cohort = get_object_or_404(Cohort, id=cohort_id)
    raw_phone = request.POST.get('phone_number')
    
    if not raw_phone:
        messages.error(request, "Phone number is required.")
        return redirect('gamemode_detail', mode_id=mode.id)

    phone_number = normalize_phone(raw_phone)
    team_id = request.POST.get('team_id')
    team = None
    if team_id:
        team = get_object_or_404(TeamUP, id=team_id)

    # M-Pesa Integration Logic
    consumer_key = os.getenv('MPESA_CONSUMER_KEY')
    consumer_secret = os.getenv('MPESA_CONSUMER_SECRET')
    shortcode = os.getenv('MPESA_PAYBILL')
    passkey = os.getenv('MPESA_PASSKEY')
    callback_url = os.getenv('MPESA_CALLBACK_URL')
    mpesa_env = os.getenv('MPESA_ENVIRONMENT', 'sandbox')

    if not all([consumer_key, consumer_secret, shortcode, passkey, callback_url]):
        messages.error(request, "M-Pesa credentials not configured.")
        return redirect('gamemode_detail', mode_id=mode.id)

    # 1. Get Access Token
    base_url = "https://api.safaricom.co.ke" if mpesa_env == 'production' else "https://sandbox.safaricom.co.ke"
    
    auth_url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(auth_url, auth=(consumer_key, consumer_secret))
    access_token = r.json().get('access_token')

    # 2. Initiate STK Push
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
    
    payment_url = f"{base_url}/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Use mode.amount but allow override for testing if needed
    amount = int(mode.amount)
    if os.getenv('DEBUG') == 'True' and mpesa_env == 'production':
        # Safaricom Production doesn't usually allow 1 KSh, but for testing purposes
        # we might want to keep it dynamic. Let's stick to mode.amount for realism.
        pass

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": f"GM{mode.id}",
        "TransactionDesc": f"Participation in {mode.name}"
    }

    response = requests.post(payment_url, json=payload, headers=headers)
    res_data = response.json()

    if res_data.get('ResponseCode') == '0':
        # Create Pending Transaction
        MPesaTransaction.objects.create(
            merchant_request_id=res_data.get('MerchantRequestID'),
            checkout_request_id=res_data.get('CheckoutRequestID'),
            amount=mode.amount,
            phone_number=phone_number,
            user=request.user,
            cohort=cohort,
            game_mode=mode,
            team=team,
            status='PENDING'
        )
        messages.success(request, f"STK Push sent to {phone_number}. Please enter your M-Pesa PIN.")
    else:
        messages.error(request, f"Failed to initiate payment: {res_data.get('ResponseDescription')}")

    return redirect('dashboard')

@csrf_exempt
def mpesa_callback_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        stk_callback = data.get('Body', {}).get('stkCallback', {})
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')

        try:
            transaction = MPesaTransaction.objects.get(
                merchant_request_id=merchant_request_id,
                checkout_request_id=checkout_request_id
            )
            transaction.result_code = result_code
            transaction.result_description = result_desc

            if result_code == 0:
                transaction.status = 'SUCCESS'
                # Enroll user in cohort
                profile = transaction.user.profile
                transaction.cohort.participants.add(profile)
                
                # Notify User
                Notification.objects.create(
                    recipient=transaction.user,
                    message=f"Payment of KSh {transaction.amount} successful! You are now enrolled in {transaction.cohort.name}.",
                    notification_type='RESULT'
                )
            else:
                transaction.status = 'FAILED'
            
            transaction.save()
            return JsonResponse({"status": "Success"})
        except MPesaTransaction.DoesNotExist:
            return JsonResponse({"status": "Transaction not found"}, status=404)
    
    return JsonResponse({"status": "Invalid request"}, status=400)

@login_required
def respond_invite_view(request, invite_id):
    invite = get_object_or_404(TeamUPInvite, id=invite_id, invitee=request.user)
    action = request.POST.get('action')
    
    if action == 'accept':
        invite.status = 'ACCEPTED'
        invite.team.players.add(request.user)
        messages.success(request, f"Joined '{invite.team.name}'!")
        
        # Notify captain
        Notification.objects.create(
            recipient=invite.team.captain,
            actor=request.user,
            message=f"{request.user.gamer_tag} accepted your invite to '{invite.team.name}'.",
            notification_type='SYSTEM'
        )
    else:
        invite.status = 'DECLINED'
        messages.info(request, f"Declined invite to '{invite.team.name}'.")
    
    invite.save()
    return redirect('dashboard')

@login_required
def recruitment_center_view(request):
    agents = FreeAgent.objects.filter(is_active=True).order_by('-created_at')
    recruitments = SquadRecruitment.objects.filter(is_active=True).order_by('-created_at')
    
    # Check if user is already a free agent
    user_is_agent = FreeAgent.objects.filter(user=request.user, is_active=True).exists()
    
    # User's squads for recruitment posting
    user_squads = TeamUP.objects.filter(captain=request.user)
    
    game_modes = GameMode.objects.all()
    
    context = {
        'agents': agents,
        'recruitments': recruitments,
        'user_is_agent': user_is_agent,
        'user_squads': user_squads,
        'game_modes': game_modes,
    }
    return render(request, 'home/recruitment_center.html', context)

@login_required
def post_free_agent_view(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        mode_ids = request.POST.getlist('game_modes')
        
        agent, created = FreeAgent.objects.update_or_create(
            user=request.user,
            defaults={'message': message, 'is_active': True}
        )
        agent.game_modes.set(mode_ids)
        messages.success(request, "Your tactical profile is now live in the Recruitment Center.")
        return redirect('recruitment_center')
    return redirect('recruitment_center')

@login_required
def post_squad_recruitment_view(request):
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        slots_open = request.POST.get('slots_open')
        requirements = request.POST.get('requirements')
        
        team = get_object_or_404(TeamUP, id=team_id, captain=request.user)
        
        SquadRecruitment.objects.update_or_create(
            team=team,
            defaults={'slots_open': slots_open, 'requirements': requirements, 'is_active': True}
        )
        messages.success(request, f"Recruitment for {team.name} is now active.")
        return redirect('recruitment_center')
    return redirect('recruitment_center')

@login_required
def apply_to_squad_view(request, recruitment_id):
    recruitment = get_object_or_404(SquadRecruitment, id=recruitment_id)
    if recruitment.team.players.filter(id=request.user.id).exists():
        messages.info(request, "You are already in this squad.")
        return redirect('recruitment_center')
    
    if JoinRequest.objects.filter(player=request.user, team=recruitment.team, status='PENDING').exists():
        messages.info(request, "Application already sent.")
        return redirect('recruitment_center')
    
    if request.method == 'POST':
        message = request.POST.get('message')
        JoinRequest.objects.create(
            player=request.user,
            team=recruitment.team,
            message=message
        )
        
        # Notify Captain
        Notification.objects.create(
            recipient=recruitment.team.captain,
            actor=request.user,
            message=f"{request.user.gamer_tag} is applying to join your squad '{recruitment.team.name}'.",
            notification_type='INVITE', # Use INVITE type for recruitment requests too
            link=f'/squad/{recruitment.team.id}/manage/'
        )
        
        messages.success(request, "Application sent to the Captain.")
        return redirect('recruitment_center')
    
    return render(request, 'home/apply_to_squad.html', {'recruitment': recruitment})

@login_required
def manage_join_request_view(request, request_id, action):
    join_request = get_object_or_404(JoinRequest, id=request_id)
    if join_request.team.captain != request.user:
        messages.error(request, "Only the Captain can manage applications.")
        return redirect('dashboard')
    
    if action == 'approve':
        # Check capacity
        if join_request.team.players.count() >= join_request.team.game_mode.max_players:
            messages.error(request, "Squad is at maximum capacity.")
        else:
            join_request.team.players.add(join_request.player)
            join_request.status = 'APPROVED'
            join_request.save()
            
            # Notify Player
            Notification.objects.create(
                recipient=join_request.player,
                actor=request.user,
                message=f"Your request to join '{join_request.team.name}' has been APPROVED!",
                notification_type='SYSTEM',
                link='/dashboard/'
            )
            messages.success(request, f"Approved! {join_request.player.gamer_tag} added to roster.")
            
    elif action == 'reject':
        join_request.status = 'REJECTED'
        join_request.save()
        messages.info(request, "Application rejected.")
        
    return redirect('manage_squad', team_id=join_request.team.id)

@login_required
def deactivate_recruitment_view(request, recruitment_id):
    recruitment = get_object_or_404(SquadRecruitment, id=recruitment_id)
    if recruitment.team.captain == request.user:
        recruitment.is_active = False
        recruitment.save()
        messages.success(request, "Recruitment post closed.")
    return redirect('recruitment_center')

@login_required
def deactivate_free_agent_view(request):
    FreeAgent.objects.filter(user=request.user).update(is_active=False)
    messages.success(request, "You are no longer listed as a Free Agent.")
    return redirect('recruitment_center')

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /dashboard/",
        "Disallow: /squad/",
        "Disallow: /mpesa/",
        "Sitemap: https://cod.arrotechsolutions.com/sitemap.xml"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

@csrf_exempt
def sitemap_view(request):
    from django.contrib.sitemaps.views import sitemap as django_sitemap
    from .sitemaps import StaticViewSitemap, GameModeSitemap
    
    sitemaps = {
        'static': StaticViewSitemap,
        'gamemodes': GameModeSitemap,
    }
    
    response = django_sitemap(request, sitemaps=sitemaps)
    
    # Force clean headers for Google Crawler
    if 'X-Robots-Tag' in response:
        del response['X-Robots-Tag']
    
    # Remove Vary: Cookie which can confuse crawlers on static sitemaps
    if 'Vary' in response:
        del response['Vary']
        
    return response
    
@login_required
def notifications_view(request):
    notifications = request.user.notifications.all()
    # Mark all as read when viewed? Or provide a specific view for it.
    # For now, let's just show them.
    return render(request, 'home/notifications.html', {'notifications': notifications})

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    if notification.link:
        return redirect(notification.link)
    return redirect('notifications')

def bracket_view(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id)
    stages = GameStage.objects.filter(cohort=cohort).order_by('order')
    
    bracket_data = []
    for stage in stages:
        stage_fixtures = Fixture.objects.filter(cohort=cohort, stage=stage)
        team_fixtures = TeamUPFixture.objects.filter(cohort=cohort, stage=stage)
        bracket_data.append({
            'stage': stage,
            'solo_fixtures': stage_fixtures,
            'team_fixtures': team_fixtures
        })
    
    return render(request, 'home/brackets.html', {'cohort': cohort, 'bracket_data': bracket_data})
@csrf_exempt
def ai_chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            messages = data.get('messages', [])
            
            if not messages:
                return JsonResponse({'error': 'No messages provided'}, status=400)
            
            # Fetch platform context
            from .models import GameMode, Cohort
            
            modes_info = []
            for mode in GameMode.objects.all():
                modes_info.append(f"- {mode.name}: {mode.description} (Fee: KES {mode.amount}, Max Players: {mode.max_players})")
            
            cohorts_info = []
            for cohort in Cohort.objects.filter(status__in=['registration_ongoing', 'running']).order_by('start_date'):
                cohorts_info.append(f"- {cohort.name}: Status: {cohort.get_status_display()}, Closes: {cohort.closes_at.strftime('%Y-%m-%d')}")
                
            platform_context = "AVAILABLE MODES:\n" + "\n".join(modes_info) + "\n\nACTIVE COHORTS:\n" + "\n".join(cohorts_info)
            
            response_text = ai_service.generate_response(messages, context=platform_context)
            return JsonResponse({'response': response_text})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)
