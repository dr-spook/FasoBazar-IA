"""
FasoBazar IA — Webhook Twilio WhatsApp (version complète multilingue)
Gère : notes vocales, texte libre, commandes, réponses en Mooré/Dioula/Fr
"""
import logging
import requests

from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone

from apps.core.models import Trader, Transaction, TrustScore
from apps.core.services import (
    create_transaction, get_daily_summary, refresh_trust_score,
    transcribe_audio, extract_entities, oz_pipeline,
)
from apps.core.fixtures_config import FIXTURES_BY_ID, get_whatsapp_response

logger = logging.getLogger(__name__)

# Sessions en mémoire (réinitialisées au redémarrage — OK pour MVP)
_oz_sessions: dict[str, bool]  = {}
_pending_tx:  dict[str, dict]  = {}  # transactions en attente de clarification type


def twiml_msg(text: str) -> HttpResponse:
    """Réponse TwiML Message."""
    safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    xml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe}</Message></Response>'
    return HttpResponse(xml, content_type='text/xml; charset=utf-8')


def _clean_phone(raw: str) -> str:
    return raw.replace('whatsapp:', '').strip()


def _get_or_create_trader(phone: str) -> Trader:
    clean = _clean_phone(phone)
    trader, created = Trader.objects.get_or_create(
        phone=clean,
        defaults={'name': f'Commerçante {clean[-4:]}', 'language': 'moore'},
    )
    if created:
        refresh_trust_score(trader)
        logger.info(f'[WEBHOOK] Nouveau trader : {clean}')
    return trader


def _get_score(trader: Trader) -> TrustScore:
    try:
        return trader.trust_score
    except TrustScore.DoesNotExist:
        return refresh_trust_score(trader)


@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):

    def post(self, request):
        from_num   = request.POST.get('From', '')
        body       = request.POST.get('Body', '').strip()
        num_media  = int(request.POST.get('NumMedia', 0))
        media_url  = request.POST.get('MediaUrl0', '')
        media_type = request.POST.get('MediaContentType0', '')

        if not from_num:
            return HttpResponse('Bad Request', status=400)

        logger.info(f'[WA] from={from_num} media={num_media} body="{body[:40]}"')

        is_oz  = _oz_sessions.get(from_num, False)
        trader = _get_or_create_trader(from_num)
        lang   = trader.language  # 'moore' | 'dioula' | 'fr'

        # ── Commandes texte ─────────────────────────────────────────────
        if body:
            cmd = body.lower().strip()

            # Réponse à une clarification en attente (VENTE / ACHAT)
            if cmd in ('vente', 'achat') and from_num in _pending_tx:
                tx_type = cmd.upper()
                pending = _pending_tx.pop(from_num)
                return self._save_and_reply(
                    trader, pending['product'], pending['amount'],
                    tx_type, pending.get('transcript', ''), 'WHATSAPP', is_oz
                )

            if cmd in ('/aide', '/help', 'aide', 'help'):
                return twiml_msg(get_whatsapp_response(lang, 'AIDE'))

            if cmd in ('/bilan', 'bilan', 'mon bilan'):
                summary = get_daily_summary(trader, timezone.now().date())
                return twiml_msg(get_whatsapp_response(lang, 'BILAN',
                    ventes=f"{summary['total_ventes']:,}".replace(',', ' '),
                    achats=f"{summary['total_achats']:,}".replace(',', ' '),
                    benefice=f"{summary['benefice_net']:,}".replace(',', ' '),
                ))

            if cmd in ('/score', 'score', 'mon score'):
                score = _get_score(trader)
                return twiml_msg(get_whatsapp_response(lang, 'SCORE',
                    score=score.score,
                    status=score.status_label,
                    eligible=score.eligible_credit,
                ))

            if cmd in ('/oz', 'oz', 'mode oz'):
                _oz_sessions[from_num] = not is_oz
                etat = 'ACTIVÉ' if not is_oz else 'DÉSACTIVÉ'
                return twiml_msg(f'Mode démo {etat}.')

            if cmd in ('/reset',):
                trader.transactions.filter(created_at__date=timezone.now().date()).delete()
                refresh_trust_score(trader)
                return twiml_msg('Transactions du jour supprimées.')

            # Texte libre → essayer d'extraire directement
            if is_oz:
                result = oz_pipeline(delay_ms=0)
                return self._save_and_reply(
                    trader, result['product'], result['amount'],
                    result['type'], result['transcript'], 'WHATSAPP', True
                )

            extraction = extract_entities(body)
            return self._handle_extraction(trader, extraction, body, from_num, is_oz)

        # ── Note vocale ──────────────────────────────────────────────────
        if num_media > 0 and media_url and 'audio' in media_type:
            return self._handle_audio(trader, media_url, media_type, from_num, is_oz)

        # ── Fallback ─────────────────────────────────────────────────────
        lang = trader.language
        return twiml_msg(get_whatsapp_response(lang, 'INCONNU'))

    # ────────────────────────────────────────────────────────────────────
    def _handle_audio(self, trader, media_url, media_type, from_num, is_oz):
        lang = trader.language

        if is_oz:
            result = oz_pipeline(delay_ms=0)
            return self._save_and_reply(
                trader, result['product'], result['amount'],
                result['type'], result['transcript'], 'WHATSAPP', True
            )

        try:
            auth      = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            resp      = requests.get(media_url, auth=auth, timeout=10)
            resp.raise_for_status()
            audio     = resp.content
            transcript = transcribe_audio(audio, media_type)

            if not transcript or len(transcript.strip()) < 2:
                return twiml_msg(get_whatsapp_response(lang, 'INCONNU'))

            extraction = extract_entities(transcript)
            return self._handle_extraction(trader, extraction, transcript, from_num, is_oz)

        except Exception as e:
            logger.error(f'[WA audio] {e}')
            # Fallback automatique Mode Oz si IA échoue
            logger.info('[WA audio] Fallback Mode Oz automatique')
            result = oz_pipeline(delay_ms=0)
            return self._save_and_reply(
                trader, result['product'], result['amount'],
                result['type'], result['transcript'], 'WHATSAPP', True
            )

    def _handle_extraction(self, trader, extraction, transcript, from_num, is_oz):
        lang       = trader.language
        product    = extraction.get('product', '')
        amount     = extraction.get('amount', 0)
        tx_type    = extraction.get('type')
        confidence = extraction.get('confidence', 0)

        if amount <= 0 or not product or product == 'Inconnu':
            return twiml_msg(get_whatsapp_response(lang, 'INCONNU'))

        # Type ambigu → demander VENTE ou ACHAT
        if not tx_type or confidence < 0.65:
            _pending_tx[from_num] = {
                'product':    product,
                'amount':     amount,
                'transcript': transcript,
            }
            amt_fmt = f"{amount:,}".replace(',', ' ')
            clarif = {
                'moore':  f"M wʋma: {product} — {amt_fmt} FCFA\nVENTE walla ACHAT?",
                'dioula': f"N ye: {product} — {amt_fmt} FCFA\nFEERE (VENTE) walla SAN (ACHAT)?",
                'fr':     f"J'ai compris : {product} — {amt_fmt} FCFA\nC'est une VENTE ou un ACHAT ?",
            }
            return twiml_msg(clarif.get(lang, clarif['fr']))

        return self._save_and_reply(
            trader, product, amount, tx_type, transcript, 'WHATSAPP', is_oz
        )

    def _save_and_reply(self, trader, product, amount, tx_type, transcript, source, is_oz):
        lang = trader.language
        try:
            tx, score = create_transaction(
                trader=trader,
                product=product,
                amount=amount,
                tx_type=tx_type,
                source=source,
                raw_transcript=transcript,
            )
            amt_fmt = f"{amount:,}".replace(',', ' ')
            msg = get_whatsapp_response(
                lang, tx_type,
                amount=amt_fmt,
                product=product,
                score=score.score,
            )
            return twiml_msg(msg)
        except Exception as e:
            logger.error(f'[WA save] {e}')
            return twiml_msg('Erreur. Réessaie.')
        
def _try_update_name_from_intro(trader, transcript: str):
    """Si le commerçant s'appelle encore 'Commerçante XXXX', tente d'extraire son nom."""
    if not trader.name.startswith('Commerçante'):
        return  # Nom déjà connu
    from apps.core.services import extract_name_from_intro
    name = extract_name_from_intro(transcript)
    if name:
        trader.name = name
        trader.save(update_fields=['name'])
        logger.info(f'[WEBHOOK] Nom mis à jour : {name}')