from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Squad
from . import cricapi_service


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
    players = cricapi_service.search_players(query) if query else []
    return render(request, 'my_app/player_search.html', {'players': players, 'query': query})


@login_required(login_url='users:login')
def player_stats_view(request, player_id):
    stats = cricapi_service.get_player_stats(player_id)
    return render(request, 'my_app/player_stats.html', {'stats': stats})