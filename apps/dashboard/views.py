"""
FasoBazar IA — Vues HTML
Interface commerçante + Dashboard IMF (public) + Page Démo
"""
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.db.models import Q

from apps.core.models import Trader, Transaction, TrustScore
from apps.auth_trader.views import get_logged_trader
from apps.core.services import get_daily_summary, refresh_trust_score
from apps.core.fixtures_config import AUDIO_FIXTURES

DEMO_TRADER_ID = '00000000-0000-0000-0000-000000000001'


def _get_trader(request):
    """Retourne le trader connecté ou le trader démo par défaut."""
    return get_logged_trader(request) or get_object_or_404(Trader, id=DEMO_TRADER_ID)


class HomeView(View):
    def get(self, request):
        trader = _get_trader(request)
        try:
            score = trader.trust_score
        except TrustScore.DoesNotExist:
            score = refresh_trust_score(trader)
        today      = timezone.now().date()
        summary    = get_daily_summary(trader, today)
        recent_txs = trader.transactions.all()[:5]
        return render(request, 'dashboard/home.html', {
            'trader': trader, 'score': score, 'summary': summary,
            'recent_txs': recent_txs, 'active': 'home',
        })


class JournalView(View):
    def get(self, request):
        trader   = _get_trader(request)
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        try:
            from datetime import date
            filter_date = date.fromisoformat(date_str)
        except ValueError:
            filter_date = timezone.now().date()
        transactions = trader.transactions.filter(created_at__date=filter_date)
        summary      = get_daily_summary(trader, filter_date)
        today        = timezone.now().date()
        yesterday    = today - timedelta(days=1)
        return render(request, 'dashboard/journal.html', {
            'trader': trader, 'transactions': transactions, 'summary': summary,
            'active_date': filter_date, 'today': today, 'yesterday': yesterday,
            'active': 'journal',
        })


class ScoreView(View):
    def get(self, request):
        trader   = _get_trader(request)
        score, _ = TrustScore.objects.get_or_create(trader=trader)
        tips = [
            "Enregistre tes ventes chaque jour",
            "Note aussi tes achats et dépenses",
            "Continue pendant 30 jours sans interruption",
        ]
        if score.transaction_count < 3:
            remaining = 3 - score.transaction_count
            message = f"Plus que {remaining} transaction{'s' if remaining > 1 else ''} pour débloquer ton score !"
        elif score.score >= 700:
            message = "Excellent ! Tu es une commerçante de confiance. Les banques peuvent te faire confiance."
        elif score.score >= 300:
            message = "Bien ! Continue pour renforcer ton score et accéder à plus de crédit."
        else:
            message = "Bon début ! Chaque transaction enregistrée augmente ta crédibilité."

        credit_estimate = 0
        if score.eligible_credit:
            credit_estimate = min(500_000, int(score.total_revenue) * 2)

        return render(request, 'dashboard/score.html', {
            'trader': trader, 'score': score, 'tips': tips,
            'message': message, 'credit_estimate': credit_estimate,
            'active': 'score',
        })


class ImfDashboardView(View):
    def get(self, request):
        query   = request.GET.get('q', '').strip()
        traders = Trader.objects.prefetch_related('trust_score').all()
        if query:
            traders = traders.filter(
                Q(name__icontains=query) | Q(phone__icontains=query)
            )
        trader_data = []
        for trader in traders:
            try:
                score = trader.trust_score
            except TrustScore.DoesNotExist:
                score = refresh_trust_score(trader)
            trader_data.append({'trader': trader, 'score': score})
        trader_data.sort(key=lambda x: x['score'].score, reverse=True)
        total_eligible  = sum(1 for d in trader_data if d['score'].eligible_credit)
        total_confirmes = sum(1 for d in trader_data if d['score'].status == 'CONFIRME')
        total_revenue   = sum(int(d['score'].total_revenue) for d in trader_data)
        return render(request, 'dashboard/imf.html', {
            'trader_data':     trader_data,
            'total_traders':   len(trader_data),
            'total_eligible':  total_eligible,
            'total_confirmes': total_confirmes,
            'total_revenue':   f"{total_revenue:,}".replace(',', ' '),
            'query':           query,
        })


class ImfTraderDetailView(View):
    def get(self, request, trader_id):
        trader       = get_object_or_404(Trader, id=trader_id)
        score, _     = TrustScore.objects.get_or_create(trader=trader)
        transactions = trader.transactions.all()[:30]
        summary      = get_daily_summary(trader)
        credit_estimate = 0
        if score.eligible_credit:
            credit_estimate = min(500_000, int(score.total_revenue) * 2)
        return render(request, 'dashboard/imf_detail.html', {
            'trader': trader, 'score': score,
            'transactions': transactions, 'summary': summary,
            'credit_estimate': f"{credit_estimate:,}".replace(',', ' '),
        })


class DemoView(View):
    def get(self, request):
        fixtures_data = []
        for fx in AUDIO_FIXTURES:
            fixtures_data.append({
                'id':               fx['id'],
                'langue':           fx['langue'],
                'langue_label':     fx['langue_label'],
                'script':           fx['script'],
                'traduction':       fx['traduction'],
                'file':             fx['file'],
                'expected_type':    fx['oz_result']['type'],
                'expected_product': fx['oz_result']['product'],
                'expected_amount':  fx['oz_result']['amount'],
            })
        return render(request, 'dashboard/demo.html', {
            'fixtures':  fixtures_data,
            'trader_id': DEMO_TRADER_ID,
        })