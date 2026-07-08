"""
FasoBazar IA — Endpoints API JSON
Tous les endpoints retournent {'success': bool, 'data': ..., 'error': ...}
"""
import json
import logging
from datetime import date

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Sum, Count, Q

from apps.core.models import Trader, Transaction, TrustScore
from apps.core.services import (
    create_transaction, refresh_trust_score, get_daily_summary,
    transcribe_audio, extract_entities, oz_pipeline, compute_sca,
)

logger = logging.getLogger(__name__)

DEMO_TRADER_ID = '00000000-0000-0000-0000-000000000001'


def ok(data, status=200, meta=None):
    payload = {'success': True, 'data': data, 'error': None}
    if meta:
        payload['meta'] = meta
    return JsonResponse(payload, status=status)


def err(code, message, status=400, details=None):
    payload = {'success': False, 'data': None, 'error': {'code': code, 'message': message}}
    if details:
        payload['error']['details'] = details
    return JsonResponse(payload, status=status)


# ═══════════════════════════════════════════════════════════
# POST /api/transcribe/
# Reçoit un fichier audio, retourne transcript + extraction IA
# Header X-Oz-Mode: true → simule le pipeline
# ═══════════════════════════════════════════════════════════
@method_decorator(csrf_exempt, name='dispatch')
class TranscribeView(View):
    def post(self, request):
        # Mode Oz ?
        if request.headers.get('X-Oz-Mode') == 'true':
            result = oz_pipeline(delay_ms=2500)
            return ok(result)

        audio_file = request.FILES.get('audio')
        if not audio_file:
            return err('VALIDATION_ERROR', 'Fichier audio requis', 400)

        if audio_file.size > 25 * 1024 * 1024:
            return err('FILE_TOO_LARGE', 'Fichier trop volumineux (max 25 Mo)', 413)

        try:
            audio_bytes = audio_file.read()
            mime_type   = audio_file.content_type or 'audio/webm'

            # Étape 1 : STT
            transcript = transcribe_audio(audio_bytes, mime_type)

            # Étape 2 : NLP
            extraction = extract_entities(transcript)

            return ok({
                'transcript': transcript,
                'product':    extraction['product'],
                'amount':     extraction['amount'],
                'type':       extraction['type'],
                'confidence': extraction['confidence'],
                'mode':       'REAL',
            })

        except RuntimeError as e:
            logger.error(f'[/api/transcribe] {e}')
            return err('AI_ERROR', 'Service IA indisponible. Active le Mode Oz.', 502)
        except Exception as e:
            logger.error(f'[/api/transcribe] Erreur inattendue : {e}')
            return err('SERVER_ERROR', 'Erreur interne', 500)


# ═══════════════════════════════════════════════════════════
# POST /api/transactions/   — créer une transaction
# GET  /api/transactions/?trader_id=X&date=YYYY-MM-DD
# ═══════════════════════════════════════════════════════════
@method_decorator(csrf_exempt, name='dispatch')
class TransactionsView(View):

    def post(self, request):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return err('VALIDATION_ERROR', 'JSON invalide', 400)

        trader_id      = body.get('trader_id', DEMO_TRADER_ID)
        product        = str(body.get('product', '')).strip()
        amount         = body.get('amount')
        tx_type        = body.get('type', '').upper()
        source         = body.get('source', 'WEB')
        raw_transcript = body.get('raw_transcript', '')

        if not product:
            return err('VALIDATION_ERROR', 'Produit requis', 422)
        if not amount or float(amount) <= 0:
            return err('VALIDATION_ERROR', 'Montant invalide', 422)
        if tx_type not in ('VENTE', 'ACHAT'):
            return err('VALIDATION_ERROR', "Type doit être VENTE ou ACHAT", 422)

        try:
            trader = Trader.objects.get(id=trader_id)
        except Trader.DoesNotExist:
            return err('NOT_FOUND', 'Commerçante introuvable', 404)

        try:
            tx, score = create_transaction(
                trader=trader,
                product=product,
                amount=int(float(amount)),
                tx_type=tx_type,
                source=source,
                raw_transcript=raw_transcript,
            )
        except ValueError as e:
            return err('VALIDATION_ERROR', str(e), 422)

        return ok({
            'transaction': _tx_to_dict(tx),
            'new_score':   score.score,
        }, status=201)

    def get(self, request):
        trader_id  = request.GET.get('trader_id', DEMO_TRADER_ID)
        date_param = request.GET.get('date')

        try:
            trader = Trader.objects.get(id=trader_id)
        except Trader.DoesNotExist:
            return err('NOT_FOUND', 'Commerçante introuvable', 404)

        qs = trader.transactions.all()
        if date_param:
            try:
                filter_date = date.fromisoformat(date_param)
                qs = qs.filter(created_at__date=filter_date)
            except ValueError:
                return err('VALIDATION_ERROR', 'Format date invalide (YYYY-MM-DD)', 400)

        summary = get_daily_summary(trader, date_param)

        return ok(
            {
                'transactions':  [_tx_to_dict(tx) for tx in qs[:50]],
                'daily_summary': summary,
            },
            meta={'total': qs.count()},
        )


# ═══════════════════════════════════════════════════════════
# GET /api/traders/<id>/score/
# ═══════════════════════════════════════════════════════════
class TraderScoreView(View):
    def get(self, request, trader_id):
        try:
            trader = Trader.objects.get(id=trader_id)
        except Trader.DoesNotExist:
            return err('NOT_FOUND', 'Commerçante introuvable', 404)

        score, _ = TrustScore.objects.get_or_create(trader=trader)
        return ok({
            'score':             score.score,
            'transaction_count': score.transaction_count,
            'total_revenue':     int(score.total_revenue),
            'status':            score.status,
            'status_label':      score.status_label,
            'eligible_credit':   score.eligible_credit,
        })


# ═══════════════════════════════════════════════════════════
# GET /api/dashboard/   — dashboard IMF (proxy server-side)
# ═══════════════════════════════════════════════════════════
class DashboardView(View):
    def get(self, request):
        traders = Trader.objects.prefetch_related('trust_score').all()

        items = []
        for trader in traders:
            try:
                score = trader.trust_score
            except TrustScore.DoesNotExist:
                score = refresh_trust_score(trader)

            items.append({
                'id':                str(trader.id),
                'name':              trader.name,
                'phone':             trader.phone,
                'language':          trader.language,
                'score':             score.score,
                'transaction_count': score.transaction_count,
                'total_revenue':     int(score.total_revenue),
                'status':            score.status,
                'status_label':      score.status_label,
                'eligible_credit':   score.eligible_credit,
            })

        # Trier par score décroissant
        items.sort(key=lambda x: x['score'], reverse=True)

        global_stats = {
            'total_traders':  len(items),
            'total_eligible': sum(1 for i in items if i['eligible_credit']),
            'total_revenue':  sum(i['total_revenue'] for i in items),
        }

        return ok({'traders': items, 'global_stats': global_stats},
                  meta={'total': len(items)})


# ═══════════════════════════════════════════════════════════
# GET /api/health/
# ═══════════════════════════════════════════════════════════
class HealthView(View):
    def get(self, request):
        try:
            count = Trader.objects.count()
            return ok({'status': 'ok', 'db': 'connected', 'traders': count})
        except Exception as e:
            return JsonResponse({'status': 'degraded', 'db': str(e)}, status=503)


# ─── Helpers ────────────────────────────────────────────────

def _tx_to_dict(tx: Transaction) -> dict:
    return {
        'id':             str(tx.id),
        'trader_id':      str(tx.trader_id),
        'product':        tx.product,
        'amount':         tx.amount_int,
        'amount_fmt':     tx.amount_formatted,
        'type':           tx.type,
        'source':         tx.source,
        'raw_transcript': tx.raw_transcript or '',
        'created_at':     tx.created_at.isoformat(),
        'time_fmt':       tx.created_at.strftime('%Hh%M'),
    }


# ═══════════════════════════════════════════════════════════
# GET /api/fixtures/   — liste des cas de test audio
# POST /api/fixtures/<id>/play/ — jouer un fixture (Mode Oz ou IA réelle)
# ═══════════════════════════════════════════════════════════
from apps.core.fixtures_config import AUDIO_FIXTURES, FIXTURES_BY_ID

class FixturesListView(View):
    """Liste des 10 cas de test audio pour la page de démo."""
    def get(self, request):
        data = []
        for f in AUDIO_FIXTURES:
            data.append({
                'id':          f['id'],
                'langue':      f['langue'],
                'langue_label':f['langue_label'],
                'script':      f['script'],
                'traduction':  f['traduction'],
                'file_url':    f'/static/{f["file"]}',
                'expected': {
                    'product': f['oz_result']['product'],
                    'amount':  f['oz_result']['amount'],
                    'type':    f['oz_result']['type'],
                },
            })
        return ok({'fixtures': data, 'total': len(data)})


@method_decorator(csrf_exempt, name='dispatch')
class FixturePlayView(View):
    """
    Joue un fixture audio.
    Si is_oz=true ou si Groq échoue → utilise le résultat pré-défini du fixture.
    """
    def post(self, request, fixture_id):
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            body = {}

        fixture = FIXTURES_BY_ID.get(fixture_id)
        if not fixture:
            return err('NOT_FOUND', f'Fixture {fixture_id} introuvable', 404)

        trader_id = body.get('trader_id', DEMO_TRADER_ID)
        is_oz     = body.get('is_oz', False) or request.headers.get('X-Oz-Mode') == 'true'

        try:
            trader = Trader.objects.get(id=trader_id)
        except Trader.DoesNotExist:
            return err('NOT_FOUND', 'Commerçante introuvable', 404)

        if is_oz:
            # Utiliser le résultat pré-défini du fixture
            oz = fixture['oz_result']
            try:
                tx, score = create_transaction(
                    trader=trader,
                    product=oz['product'],
                    amount=oz['amount'],
                    tx_type=oz['type'],
                    source='OZ',
                    raw_transcript=oz['transcript'],
                )
                return ok({
                    'transaction': _tx_to_dict(tx),
                    'new_score':   score.score,
                    'transcript':  oz['transcript'],
                    'mode':        'OZ',
                    'fixture_id':  fixture_id,
                    'langue':      fixture['langue'],
                }, status=201)
            except Exception as e:
                return err('SERVER_ERROR', str(e), 500)

        # Mode réel : lire le fichier audio et envoyer à Groq
        import os
        from django.conf import settings as django_settings
        audio_path = os.path.join(django_settings.BASE_DIR, 'static', fixture['file'])

        if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 1000:
            # Fichier placeholder → fallback automatique sur le résultat Oz
            logger.warning(f'[FIXTURE] {fixture_id}: fichier placeholder détecté → fallback Oz')
            oz = fixture['oz_result']
            try:
                tx, score = create_transaction(
                    trader=trader,
                    product=oz['product'],
                    amount=oz['amount'],
                    tx_type=oz['type'],
                    source='OZ',
                    raw_transcript=f"[FIXTURE PLACEHOLDER] {oz['transcript']}",
                )
                return ok({
                    'transaction': _tx_to_dict(tx),
                    'new_score':   score.score,
                    'transcript':  oz['transcript'],
                    'mode':        'OZ_FALLBACK',
                    'fixture_id':  fixture_id,
                    'langue':      fixture['langue'],
                    'note':        'Fichier audio placeholder — remplacez par le vrai enregistrement',
                }, status=201)
            except Exception as e:
                return err('SERVER_ERROR', str(e), 500)

        # Vrai fichier audio → pipeline Groq
        try:
            with open(audio_path, 'rb') as f:
                audio_bytes = f.read()

            from apps.core.services import transcribe_audio as stt, extract_entities as nlp
            transcript = stt(audio_bytes, 'audio/wav')
            extraction = nlp(transcript)

            product    = extraction['product']
            amount     = extraction['amount']
            tx_type    = extraction['type'] or fixture['oz_result']['type']
            confidence = extraction['confidence']

            if amount <= 0 or not product:
                raise ValueError('Extraction insuffisante')

            tx, score = create_transaction(
                trader=trader,
                product=product,
                amount=amount,
                tx_type=tx_type,
                source='REAL',
                raw_transcript=transcript,
            )
            return ok({
                'transaction': _tx_to_dict(tx),
                'new_score':   score.score,
                'transcript':  transcript,
                'confidence':  confidence,
                'mode':        'REAL',
                'fixture_id':  fixture_id,
                'langue':      fixture['langue'],
            }, status=201)

        except Exception as e:
            logger.warning(f'[FIXTURE] {fixture_id} IA échoué : {e} → fallback Oz')
            # Fallback automatique sur Oz
            oz = fixture['oz_result']
            try:
                tx, score = create_transaction(
                    trader=trader,
                    product=oz['product'],
                    amount=oz['amount'],
                    tx_type=oz['type'],
                    source='OZ',
                    raw_transcript=oz['transcript'],
                )
                return ok({
                    'transaction': _tx_to_dict(tx),
                    'new_score':   score.score,
                    'transcript':  oz['transcript'],
                    'mode':        'OZ_FALLBACK',
                    'fixture_id':  fixture_id,
                    'langue':      fixture['langue'],
                }, status=201)
            except Exception as e2:
                return err('SERVER_ERROR', str(e2), 500)