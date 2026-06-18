from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Squad, Player, SquadPlayer, Coach
from .forms import SquadForm
from . import cricapi_service, ratings

SQUAD_SLOTS = range(1, 12)

BOWLING_SLOT_LABELS = [
    "Opening Bowler 1", "Opening Bowler 2",
    "1st Change Bowler 1", "1st Change Bowler 2",
    "2nd Change Bowler 1", "2nd Change Bowler 2",
    "Part Time Bowler 1", "Part Time Bowler 2",
]

COACH_ROLES = {'head': 'Head Coach', 'assistant': 'Assistant Coach'}

# (label, x, y) — coordinates placed by hand on a 400x400 field diagram to
# roughly match a real fielding chart (slips/fine leg near the keeper at the
# top, long-on/long-off out in front at the bottom). Not claiming exact
# textbook angles, just a visual spread around the pitch.
FIELDING_POSITIONS = [
    ("Fine Leg", 120, 75),
    ("Short Fine Leg", 180, 55),
    ("Slip 1", 205, 115),
    ("Slip 2", 175, 135),
    ("Gully", 150, 160),
    ("Point", 120, 195),
    ("Extra Cover", 80, 170),
    ("Backward Point", 55, 220),
    ("Cover", 100, 250),
    ("Mid-off", 155, 285),
    ("Mid-on", 245, 285),
    ("Mid-wicket", 295, 250),
    ("Square-Leg", 320, 170),
    ("Deep Backward Square-Leg", 345, 215),
    ("Deep Mid-wicket", 335, 260),
    ("Long-on", 265, 330),
    ("Long-off", 180, 350),
]


def _team_ratings(squad):
    """Batting/bowling/overall ratings out of 100 for a squad.

    Batting rating is the average overall_rating of batsmen/all-rounders/
    wicketkeepers, plus the head coach's and assistant coach's win_rate as
    extra data points if assigned. Bowling rating is the same idea for
    bowlers/all-rounders, also including both coaches' win_rate (an
    all-rounder, and each coach, count toward both groups). Overall is the
    average of the two. If a group ends up empty, it falls back to
    whichever group does have a value rather than treating the missing one
    as a zero.
    """
    squad_players = squad.players.select_related('player', 'player__role', 'player__stats').all()
    rated = [sp.player.stats for sp in squad_players if hasattr(sp.player, 'stats') and sp.player.stats.overall_rating is not None]

    batting_ratings = []
    bowling_ratings = []
    for stats in rated:
        role = stats.player.role.role_name if stats.player.role else ""
        category = ratings.role_category(role)
        if category in ("batsman", "allrounder"):
            batting_ratings.append(stats.overall_rating)
        if category in ("bowler", "allrounder"):
            bowling_ratings.append(stats.overall_rating)

    for coach in (squad.coach, squad.assistant_coach):
        if coach and coach.win_rate is not None:
            coach_rating = float(coach.win_rate)
            batting_ratings.append(coach_rating)
            bowling_ratings.append(coach_rating)

    batting_rating = round(sum(batting_ratings) / len(batting_ratings)) if batting_ratings else None
    bowling_rating = round(sum(bowling_ratings) / len(bowling_ratings)) if bowling_ratings else None

    if batting_rating is not None and bowling_rating is not None:
        overall = round((batting_rating + bowling_rating) / 2)
    else:
        overall = batting_rating if batting_rating is not None else bowling_rating

    return {'batting': batting_rating, 'bowling': bowling_rating, 'overall': overall}


@login_required(login_url='users:login')
def home_view(request):
    squads = Squad.objects.filter(user=request.user).prefetch_related('players__player')
    live_scores = cricapi_service.get_live_scores()[:3]
    fixtures = cricapi_service.get_fixtures()[:3]
    return render(request, 'my_app/home.html', {
        'squads': squads,
        'live_scores': live_scores,
        'fixtures': fixtures,
    })


@login_required(login_url='users:login')
def squad_create_view(request):
    if request.method == 'POST':
        form = SquadForm(request.POST)
        if form.is_valid():
            squad = form.save(commit=False)
            squad.user = request.user
            squad.save()
            return redirect('my_app:squad_detail', squad_id=squad.id)
    else:
        form = SquadForm()
    return render(request, 'my_app/squad_form.html', {'form': form})


@login_required(login_url='users:login')
def squad_detail_view(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    squad_players = squad.players.select_related('player', 'player__role', 'player__stats').all()

    return render(request, 'my_app/squad_detail.html', {
        'squad': squad,
        'squad_players': squad_players,
        'ratings': _team_ratings(squad),
    })


@login_required(login_url='users:login')
def squad_batting_lineup_view(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    squad_players = squad.players.select_related('player', 'player__role', 'player__stats').all()

    assigned = {sp.batting_order: sp for sp in squad_players if sp.batting_order}
    lineup = [{'slot': slot, 'squad_player': assigned.get(slot)} for slot in SQUAD_SLOTS]

    return render(request, 'my_app/squad_batting_lineup.html', {
        'squad': squad,
        'lineup': lineup,
        'ratings': _team_ratings(squad),
    })


@login_required(login_url='users:login')
def squad_slot_view(request, squad_id, slot):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)

    if request.method == 'POST':
        player = get_object_or_404(Player, id=request.POST.get('player_id'))
        SquadPlayer.objects.filter(
            squad=squad, batting_order=slot, is_substitute=False
        ).exclude(player=player).update(batting_order=None)
        SquadPlayer.objects.update_or_create(
            squad=squad, player=player,
            defaults={'batting_order': slot},
        )
        return redirect('my_app:squad_batting_lineup', squad_id=squad.id)

    query = request.GET.get('q', '').strip()
    results = Player.objects.filter(name__icontains=query).select_related('role', 'stats') if query else []
    return render(request, 'my_app/squad_slot.html', {
        'squad': squad,
        'slot': slot,
        'query': query,
        'results': results,
    })


@login_required(login_url='users:login')
def squad_bowling_lineup_view(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    squad_players = squad.players.select_related('player', 'player__role', 'player__stats').all()

    assigned = {sp.bowling_order: sp for sp in squad_players if sp.bowling_order}
    lineup = [
        {'slot': i + 1, 'label': label, 'squad_player': assigned.get(i + 1)}
        for i, label in enumerate(BOWLING_SLOT_LABELS)
    ]

    return render(request, 'my_app/squad_bowling_lineup.html', {
        'squad': squad,
        'lineup': lineup,
        'ratings': _team_ratings(squad),
    })


@login_required(login_url='users:login')
def squad_bowling_slot_view(request, squad_id, slot):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    label = BOWLING_SLOT_LABELS[slot - 1] if 1 <= slot <= len(BOWLING_SLOT_LABELS) else f"Bowler {slot}"

    if request.method == 'POST':
        player = get_object_or_404(Player, id=request.POST.get('player_id'))
        SquadPlayer.objects.filter(
            squad=squad, bowling_order=slot, is_substitute=False
        ).exclude(player=player).update(bowling_order=None)
        SquadPlayer.objects.update_or_create(
            squad=squad, player=player,
            defaults={'bowling_order': slot},
        )
        return redirect('my_app:squad_bowling_lineup', squad_id=squad.id)

    query = request.GET.get('q', '').strip()
    results = Player.objects.filter(name__icontains=query).select_related('role', 'stats') if query else []
    return render(request, 'my_app/squad_bowling_slot.html', {
        'squad': squad,
        'slot': slot,
        'label': label,
        'query': query,
        'results': results,
    })


@login_required(login_url='users:login')
def squad_fielding_view(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    squad_players = squad.players.select_related('player', 'player__role', 'player__stats').all()

    assigned = {sp.fielding_position: sp for sp in squad_players if sp.fielding_position}
    lineup = [
        {
            'slot': i + 1, 'label': label, 'x': x, 'y': y,
            'pill_x': x - 50, 'pill_y': y - 14,
            'squad_player': assigned.get(label),
        }
        for i, (label, x, y) in enumerate(FIELDING_POSITIONS)
    ]

    return render(request, 'my_app/squad_fielding.html', {
        'squad': squad,
        'lineup': lineup,
    })


@login_required(login_url='users:login')
def squad_fielding_slot_view(request, squad_id, slot):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    label = FIELDING_POSITIONS[slot - 1][0] if 1 <= slot <= len(FIELDING_POSITIONS) else f"Position {slot}"

    if request.method == 'POST':
        player = get_object_or_404(Player, id=request.POST.get('player_id'))
        SquadPlayer.objects.filter(
            squad=squad, fielding_position=label, is_substitute=False
        ).exclude(player=player).update(fielding_position=None)
        SquadPlayer.objects.update_or_create(
            squad=squad, player=player,
            defaults={'fielding_position': label},
        )
        return redirect('my_app:squad_fielding', squad_id=squad.id)

    query = request.GET.get('q', '').strip()
    results = Player.objects.filter(name__icontains=query).select_related('role', 'stats') if query else []
    return render(request, 'my_app/squad_fielding_slot.html', {
        'squad': squad,
        'slot': slot,
        'label': label,
        'query': query,
        'results': results,
    })


@login_required(login_url='users:login')
def squad_coaches_view(request, squad_id):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    coaches = [
        {'role': 'head', 'label': COACH_ROLES['head'], 'coach': squad.coach},
        {'role': 'assistant', 'label': COACH_ROLES['assistant'], 'coach': squad.assistant_coach},
    ]
    return render(request, 'my_app/squad_coaches.html', {
        'squad': squad,
        'coaches': coaches,
        'ratings': _team_ratings(squad),
    })


@login_required(login_url='users:login')
def squad_coach_slot_view(request, squad_id, role):
    squad = get_object_or_404(Squad, id=squad_id, user=request.user)
    label = COACH_ROLES.get(role, 'Coach')
    field_name = 'assistant_coach' if role == 'assistant' else 'coach'

    if request.method == 'POST':
        coach = get_object_or_404(Coach, id=request.POST.get('coach_id'))
        setattr(squad, field_name, coach)
        squad.save()
        return redirect('my_app:squad_coaches', squad_id=squad.id)

    query = request.GET.get('q', '').strip()
    results = Coach.objects.filter(name__icontains=query) if query else []
    return render(request, 'my_app/squad_coach_slot.html', {
        'squad': squad,
        'role': role,
        'label': label,
        'query': query,
        'results': results,
    })


@login_required(login_url='users:login')
def live_scores_view(request):
    scores = cricapi_service.get_live_scores()
    return render(request, 'my_app/live_scores.html', {'scores': scores})


@login_required(login_url='users:login')
def fixtures_view(request):
    fixtures = cricapi_service.get_fixtures()
    return render(request, 'my_app/fixtures.html', {'fixtures': fixtures})


@login_required(login_url='users:login')
def player_search_view(request):
    query = request.GET.get('q', '').strip()
    players = Player.objects.filter(name__icontains=query).select_related('role', 'stats') if query else []
    return render(request, 'my_app/player_search.html', {'players': players, 'query': query})


@login_required(login_url='users:login')
def player_stats_view(request, player_id):
    player = get_object_or_404(Player, cricapi_id=player_id)
    stats = getattr(player, 'stats', None)
    return render(request, 'my_app/player_stats.html', {'player': player, 'stats': stats})