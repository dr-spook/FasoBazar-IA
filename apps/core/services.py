import json
import logging
import time
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from .models import Trader, Transaction, TrustScore

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# CALCUL DU SCORE DE CONFIANCE ALTERNATIF (SCA) — 0 à 1000
# Formule : MIN(1000, (tx_count × 50) + (MIN(revenue, 1_000_000) / 200))
# Équivalences : 10 tx + 200K FCFA ≈ 500 pts (ELIGIBLE)
#                20 tx + 500K FCFA ≈ 700 pts (CONFIRME)
# ═══════════════════════════════════════════════════════════

def compute_sca(transaction_count: int, total_revenue: float) -> int:
    base_score    = transaction_count * 50
    revenue_bonus = min(float(total_revenue), 1_000_000) / 200
    return min(1000, int(base_score + revenue_bonus))


def refresh_trust_score(trader: Trader) -> TrustScore:
    from django.db.models import Sum, Count, Q
    stats = trader.transactions.aggregate(
        total_count=Count('id'),
        total_ventes=Sum('amount', filter=Q(type='VENTE')),
    )
    total_count   = stats['total_count'] or 0
    total_revenue = float(stats['total_ventes'] or 0)
    new_score     = compute_sca(total_count, total_revenue)

    score_obj, _ = TrustScore.objects.get_or_create(trader=trader)
    score_obj.score             = new_score
    score_obj.transaction_count = total_count
    score_obj.total_revenue     = Decimal(total_revenue)
    score_obj.save()
    return score_obj


# ═══════════════════════════════════════════════════════════
# CRÉATION DE TRANSACTION (atomique)
# ═══════════════════════════════════════════════════════════

def create_transaction(
    trader: Trader,
    product: str,
    amount: int,
    tx_type: str,
    source: str = 'WEB',
    raw_transcript: str = '',
) -> tuple:
    if tx_type not in ('VENTE', 'ACHAT'):
        raise ValueError(f"Type invalide : {tx_type}")
    if amount <= 0:
        raise ValueError(f"Montant invalide : {amount}")
    if not product.strip():
        raise ValueError("Produit requis")

    with db_transaction.atomic():
        tx = Transaction.objects.create(
            trader=trader,
            product=product.strip()[:200],
            amount=Decimal(amount),
            type=tx_type,
            source=source,
            raw_transcript=raw_transcript[:2000] if raw_transcript else '',
        )
        score = refresh_trust_score(trader)
    return tx, score


# ═══════════════════════════════════════════════════════════
# PIPELINE IA — STT (Groq Whisper) + NLP (LLaMA)
# ═══════════════════════════════════════════════════════════

NLP_SYSTEM_PROMPT = """Tu es un assistant comptable pour commerçantes africaines des marchés.
À partir du texte (français, Mooré, Dioula ou Fulfuldé), extrais en JSON UNIQUEMENT :
{"product": "nom du produit", "amount": nombre_entier_positif_en_FCFA, "type": "VENTE" ou "ACHAT" ou null, "confidence": 0.0_à_1.0}

Règles :
- product : nom du produit en français, max 100 chars
- amount : montant TOTAL en FCFA (nombre entier). Si "3 pagnes à 5000", calculer 15000.
- type : "VENTE" si argent reçu, "ACHAT" si argent dépensé, null si incertain
- confidence : honnêteté sur la qualité de l'extraction

Exemples :
"J'ai vendu 3 pagnes à 5000 francs" → {"product":"Pagnes","amount":15000,"type":"VENTE","confidence":0.97}
"Acheté du savon 2500" → {"product":"Savon","amount":2500,"type":"ACHAT","confidence":0.95}
"Mi don pagne 8000" → {"product":"Pagne","amount":8000,"type":"VENTE","confidence":0.85}
"M bê sak pagn yiib fo pusgo" → {"product":"Pagnes","amount":10000,"type":"VENTE","confidence":0.80}

Réponds UNIQUEMENT avec le JSON, sans markdown ni explication."""


def transcribe_audio(audio_bytes: bytes, mime_type: str = 'audio/webm') -> str:
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise ValueError("GROQ_API_KEY non configurée")

    ext_map = {
        'audio/webm': 'webm', 'audio/mp4': 'mp4', 'audio/mpeg': 'mp3',
        'audio/mp3': 'mp3', 'audio/wav': 'wav', 'audio/ogg': 'ogg',
        'audio/flac': 'flac', 'audio/x-m4a': 'm4a',
    }
    ext = ext_map.get(mime_type.lower(), 'webm')

    try:
        import groq
        client = groq.Groq(api_key=api_key)
        transcription = client.audio.transcriptions.create(
            file=(f'audio.{ext}', audio_bytes, mime_type),
            model='whisper-large-v3',
            language='fr',
            response_format='text',
        )
        return str(transcription).strip()
    except Exception as e:
        logger.error(f"[STT] Groq Whisper erreur : {e}")
        raise RuntimeError(f"Transcription échouée : {e}") from e


def extract_entities(transcript: str) -> dict:
    if not transcript.strip():
        return {'product': 'Inconnu', 'amount': 0, 'type': None, 'confidence': 0.0}

    try:
        result = _extract_via_groq(transcript)
        if result:
            return result
    except Exception as e:
        logger.warning(f"[NLP] Groq LLaMA échoué : {e} — tentative Gemini")

    try:
        result = _extract_via_gemini(transcript)
        if result:
            return result
    except Exception as e:
        logger.error(f"[NLP] Gemini échoué aussi : {e}")

    return {'product': 'Inconnu', 'amount': 0, 'type': None, 'confidence': 0.0}


def _extract_via_groq(transcript: str) -> dict | None:
    api_key = settings.GROQ_API_KEY
    if not api_key:
        return None
    import groq
    client = groq.Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model='llama-3.1-8b-instant',
        messages=[
            {'role': 'system', 'content': NLP_SYSTEM_PROMPT},
            {'role': 'user', 'content': transcript},
        ],
        temperature=0.1,
        max_tokens=150,
        response_format={'type': 'json_object'},
        timeout=5.0,
    )
    raw = completion.choices[0].message.content or ''
    return _parse_extraction(raw)


def _extract_via_gemini(transcript: str) -> dict | None:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return None
    url  = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}'
    body = {
        'contents': [{'parts': [{'text': f"{NLP_SYSTEM_PROMPT}\n\nTexte : \"{transcript}\""}]}],
        'generationConfig': {'temperature': 0.1, 'maxOutputTokens': 150},
    }
    resp = requests.post(url, json=body, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    raw  = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
    import re
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return _parse_extraction(match.group(0))
    return None


def _parse_extraction(raw: str) -> dict | None:
    try:
        data    = json.loads(raw)
        amount  = max(0, int(float(data.get('amount', 0))))
        tx_type = data.get('type')
        if tx_type not in ('VENTE', 'ACHAT'):
            tx_type = None
        return {
            'product':    str(data.get('product', 'Produit'))[:200],
            'amount':     amount,
            'type':       tx_type,
            'confidence': min(1.0, max(0.0, float(data.get('confidence', 0)))),
        }
    except Exception as e:
        logger.warning(f"[NLP] Parsing JSON échoué : {e}")
        return None


# ═══════════════════════════════════════════════════════════
# MODE OZ — simulateur offline
# ═══════════════════════════════════════════════════════════

def oz_pipeline(delay_ms: int = 2500) -> dict:
    time.sleep(delay_ms / 1000)
    scenario = settings.OZ_SCENARIO
    return {
        'transcript': scenario['transcript'],
        'product':    scenario['product'],
        'amount':     scenario['amount'],
        'type':       scenario['type'],
        'confidence': 0.97,
        'mode':       'OZ',
    }


# ═══════════════════════════════════════════════════════════
# INSCRIPTION WHATSAPP — capter le nom depuis la première note vocale
# ═══════════════════════════════════════════════════════════

def extract_name_from_intro(transcript: str) -> str | None:
    """
    Tente d'extraire un prénom/nom depuis un message d'introduction.
    Ex: "Je m'appelle Aminata Sawadogo" → "Aminata Sawadogo"
    """
    import re
    patterns = [
        r"(?:je m'appelle|mon nom est|je suis|i ye|m yʋʋmd|n tɔgɔ ye)\s+([A-ZÀ-Ÿa-zà-ÿ]+(?:\s+[A-ZÀ-Ÿa-zà-ÿ]+)?)",
        r"^([A-ZÀ-Ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ÿ][a-zà-ÿ]+)?)(?:\s*,|\s*\.)?\s*$",
    ]
    for pattern in patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 2 <= len(name) <= 60:
                return name.title()
    return None


# ═══════════════════════════════════════════════════════════
# SEED — données de démo
# ═══════════════════════════════════════════════════════════

DEMO_TRADERS = [
    {
        'id':       '00000000-0000-0000-0000-000000000001',
        'name':     'Aïssata Ouédraogo',
        'phone':    '+22670000001',
        'language': 'moore',
        'transactions': [
            ('Pagnes bazin',        15000, 'VENTE', 'REAL'),
            ('Savon de Marseille',   2500, 'ACHAT', 'REAL'),
            ('Pagne wax',            8000, 'VENTE', 'REAL'),
            ('Henné',                1500, 'ACHAT', 'REAL'),
            ('Pagnes bazin',        20000, 'VENTE', 'OZ'),
            ('Boubou brodé',        12000, 'VENTE', 'REAL'),
            ('Fil à broder',           800, 'ACHAT', 'REAL'),
        ],
    },
    {
        'id':       '00000000-0000-0000-0000-000000000002',
        'name':     'Mariam Sawadogo',
        'phone':    '+22670000002',
        'language': 'dioula',
        'transactions': [
            ('Tissus wax hollandais', 25000, 'VENTE', 'REAL'),
            ('Stock tissus',          10000, 'ACHAT', 'REAL'),
            ('Kente',                 18000, 'VENTE', 'REAL'),
            ('Broderie',               5000, 'VENTE', 'REAL'),
            ('Matériel couture',       3500, 'ACHAT', 'REAL'),
            ('Boubou complet',        22000, 'VENTE', 'REAL'),
            ('Pagne 6 yards',         17000, 'VENTE', 'REAL'),
            ('Nappe brodée',           8500, 'VENTE', 'REAL'),
            ('Fil soie',               2000, 'ACHAT', 'REAL'),
            ('Voile de mariée',       35000, 'VENTE', 'REAL'),
            ('Broderie express',      12000, 'VENTE', 'REAL'),
            ('Perles décoration',      4500, 'ACHAT', 'REAL'),
            ('Ensemble bogolan',      28000, 'VENTE', 'REAL'),
            ('Teinture naturelle',     3000, 'ACHAT', 'REAL'),
        ],
    },
    {
        'id':       '00000000-0000-0000-0000-000000000003',
        'name':     'Fatoumata Konaté',
        'phone':    '+22670000003',
        'language': 'fulfulde',
        'transactions': [
            ('Épices soumbala',  3500, 'VENTE', 'REAL'),
            ('Néré',             1200, 'ACHAT', 'REAL'),
            ('Épices mélangées', 4200, 'VENTE', 'REAL'),
            ('Poivre noir',      2800, 'VENTE', 'REAL'),
            ('Stock épices',     2000, 'ACHAT', 'REAL'),
        ],
    },
    {
        'id':       '00000000-0000-0000-0000-000000000004',
        'name':     'Aminata Traoré',
        'phone':    '+22670000004',
        'language': 'moore',
        'transactions': [
            ('Légumes',  1500, 'VENTE', 'REAL'),
            ('Tomates',   800, 'VENTE', 'REAL'),
        ],
    },
    {
        'id':       '00000000-0000-0000-0000-000000000005',
        'name':     'Bintou Diallo',
        'phone':    '+22670000005',
        'language': 'dioula',
        'transactions': [
            ('Or 18 carats',        45000, 'VENTE', 'REAL'),
            ('Bijoux argent',       12000, 'VENTE', 'REAL'),
            ('Pendentif or',        28000, 'VENTE', 'REAL'),
            ('Matières premières',  15000, 'ACHAT', 'REAL'),
            ('Bague or',            40000, 'VENTE', 'REAL'),
            ('Collier perles',       9000, 'VENTE', 'REAL'),
            ('Bracelet argent',      7500, 'VENTE', 'REAL'),
            ('Minerais bruts',      18000, 'ACHAT', 'REAL'),
            ('Boucles oreilles',     6000, 'VENTE', 'REAL'),
            ('Parure complète',     55000, 'VENTE', 'REAL'),
            ('Métal précieux',      22000, 'ACHAT', 'REAL'),
            ('Montre plaquée or',   35000, 'VENTE', 'REAL'),
            ('Chaîne or 14K',       48000, 'VENTE', 'REAL'),
            ('Pierres semi-préc.',   8000, 'ACHAT', 'REAL'),
            ('Bague diamant',       95000, 'VENTE', 'REAL'),
        ],
    },
]


def seed_demo_data():
    """Charge les 5 commerçantes de démo si la BDD est vide."""
    if Trader.objects.exists():
        logger.info('[SEED] Données de démo déjà présentes — skip')
        return

    logger.info('[SEED] Chargement des données de démo...')
    for data in DEMO_TRADERS:
        import os
        demo_pwd = os.getenv('DEMO_PASSWORD', 'demo2026')
        trader = Trader.objects.filter(id=data['id']).first()
        if not trader:
            trader = Trader(
                id=data['id'],
                name=data['name'],
                phone=data['phone'],
                language=data['language'],
            )
            trader.set_password(demo_pwd)
            trader.save()
        for product, amount, tx_type, source in data['transactions']:
            Transaction.objects.get_or_create(
                trader=trader,
                product=product,
                amount=amount,
                type=tx_type,
                defaults={'source': source},
            )
        refresh_trust_score(trader)
        logger.info(f'  ✓ {trader.name}')

    logger.info('[SEED] 5 commerçantes chargées.')

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def get_daily_summary(trader: Trader, date=None) -> dict:
    from django.db.models import Sum, Q
    qs = trader.transactions.all()
    if date:
        qs = qs.filter(created_at__date=date)

    result = qs.aggregate(
        total_ventes=Sum('amount', filter=Q(type='VENTE')),
        total_achats=Sum('amount', filter=Q(type='ACHAT')),
    )
    ventes = int(result['total_ventes'] or 0)
    achats = int(result['total_achats'] or 0)
    return {
        'total_ventes':  ventes,
        'total_achats':  achats,
        'benefice_net':  ventes - achats,
        'ventes_fmt':    f"{ventes:,}".replace(',', ' '),
        'achats_fmt':    f"{achats:,}".replace(',', ' '),
        'benefice_fmt':  f"{ventes - achats:,}".replace(',', ' '),
    }