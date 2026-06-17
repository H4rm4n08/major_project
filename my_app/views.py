from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Squad, Player
from .forms import SquadForm
from . import cricapi_service


def _team_rating(squad_players):
    """Rough overall rating out of 100, blending batting average and wickets across the squad."""
    rated = [sp.player.stats for sp in squad_players if hasattr(sp.player, 'stats')]
    if not rated:
        return None
    avg_batting = sum(float(s.batting_avg or 0) for s in rated) / len(rated)
    avg_wickets = sum(s.wickets_taken for s in rated) / len(rated)
    rating = (avg_batting * 1.2) + (avg_wickets * 2)
    return round(min(rating, 100))


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
        'rating': _team_rating(squad_players),
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
    players = Player.objects.filter(name__icontains=query).select_related('role') if query else []
    return render(request, 'my_app/player_search.html', {'players': players, 'query': query})


@login_required(login_url='users:login')
def player_stats_view(request, player_id):
    player = get_object_or_404(Player, cricapi_id=player_id)
    stats = getattr(player, 'stats', None)
    return render(request, 'my_app/player_stats.html', {'player': player, 'stats': stats})