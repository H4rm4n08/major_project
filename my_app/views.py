from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Squad, Player, SquadPlayer
from .forms import SquadForm
from . import cricapi_service, ratings

SQUAD_SLOTS = range(1, 12)


def _team_rating(squad_players):
    """Overall squad rating out of 100: (batting rating + bowling rating) / 2.

    Batting rating is the average overall_rating of batsmen/all-rounders/
    wicketkeepers; bowling rating is the average overall_rating of bowlers/
    all-rounders (an all-rounder counts in both groups). If the squad has
    nobody in one of the two groups, the overall rating falls back to
    whichever group does have players, rather than treating the missing
    group as a zero.
    """
    rated = [sp.player.stats for sp in squad_players if hasattr(sp.player, 'stats') and sp.player.stats.overall_rating is not None]
    if not rated:
        return None

    batting_ratings = []
    bowling_ratings = []
    for stats in rated:
        role = stats.player.role.role_name if stats.player.role else ""
        category = ratings.role_category(role)
        if category in ("batsman", "allrounder"):
            batting_ratings.append(stats.overall_rating)
        if category in ("bowler", "allrounder"):
            bowling_ratings.append(stats.overall_rating)

    batting_rating = sum(batting_ratings) / len(batting_ratings) if batting_ratings else None
    bowling_rating = sum(bowling_ratings) / len(bowling_ratings) if bowling_ratings else None

    if batting_rating is not None and bowling_rating is not None:
        return round((batting_rating + bowling_rating) / 2)
    if batting_rating is not None:
        return round(batting_rating)
    if bowling_rating is not None:
        return round(bowling_rating)
    return None


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

    assigned = {sp.batting_order: sp for sp in squad_players if sp.batting_order}
    lineup = [{'slot': slot, 'squad_player': assigned.get(slot)} for slot in SQUAD_SLOTS]

    return render(request, 'my_app/squad_detail.html', {
        'squad': squad,
        'squad_players': squad_players,
        'lineup': lineup,
        'rating': _team_rating(squad_players),
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
        return redirect('my_app:squad_detail', squad_id=squad.id)

    query = request.GET.get('q', '').strip()
    results = Player.objects.filter(name__icontains=query).select_related('role', 'stats') if query else []
    return render(request, 'my_app/squad_slot.html', {
        'squad': squad,
        'slot': slot,
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