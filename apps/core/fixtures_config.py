"""
FasoBazar IA — Configuration des fixtures audio de démo
10 cas de test (5 Mooré + 5 Dioula) avec résultats attendus.

Ces fixtures servent à :
1. Tester le pipeline IA avec de vraies langues locales
2. Fournir un Mode Oz précis par fichier si Groq rate
3. Afficher les cas de test dans l'interface de démo

IMPORTANT : Remplacer les fichiers WAV placeholder dans
static/audio/fixtures/ par les vrais enregistrements avant la démo.
"""

AUDIO_FIXTURES = [
    # ─── MOORÉ ─────────────────────────────────────────────────────────
    {
        'id':          'moore_01',
        'file':        'audio/fixtures/moore_01.wav',
        'langue':      'moore',
        'langue_label':'Mooré',
        'script':      'M bê sak a pagn yiib, yam-yam fo pusgo fo pusgo',
        'traduction':  "J'ai vendu 2 pagnes, cinq mille cinq mille",
        'oz_result': {
            'product':    'Pagnes',
            'amount':     10000,
            'type':       'VENTE',
            'confidence': 0.92,
            'transcript': 'M bê sak a pagn yiib yam-yam fo pusgo fo pusgo',
        },
        # Réponse WhatsApp en Mooré
        'whatsapp_response': {
            'VENTE': '✅ VENTE kẽenga!\nYam-yam: +{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
            'ACHAT': '✅ ACHAT kẽenga!\nYam-yam: -{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
        },
    },
    {
        'id':          'moore_02',
        'file':        'audio/fixtures/moore_02.wav',
        'langue':      'moore',
        'langue_label':'Mooré',
        'script':      'M kõ savõ yam-yam a yiib pusgo',
        'traduction':  "J'ai acheté du savon, deux mille",
        'oz_result': {
            'product':    'Savon',
            'amount':     2000,
            'type':       'ACHAT',
            'confidence': 0.90,
            'transcript': 'M kõ savõ yam-yam a yiib pusgo',
        },
        'whatsapp_response': {
            'VENTE': '✅ VENTE kẽenga!\nYam-yam: +{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
            'ACHAT': '✅ ACHAT kẽenga!\nYam-yam: -{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
        },
    },
    {
        'id':          'moore_03',
        'file':        'audio/fixtures/moore_03.wav',
        'langue':      'moore',
        'langue_label':'Mooré',
        'script':      'M bê sak a bãongo fo pusgo la yiib',
        'traduction':  "J'ai vendu des légumes, cinq mille deux cents",
        'oz_result': {
            'product':    'Légumes',
            'amount':     5200,
            'type':       'VENTE',
            'confidence': 0.88,
            'transcript': 'M bê sak a bãongo fo pusgo la yiib',
        },
        'whatsapp_response': {
            'VENTE': '✅ VENTE kẽenga!\nYam-yam: +{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
            'ACHAT': '✅ ACHAT kẽenga!\nYam-yam: -{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
        },
    },
    {
        'id':          'moore_04',
        'file':        'audio/fixtures/moore_04.wav',
        'langue':      'moore',
        'langue_label':'Mooré',
        'script':      'M kõ neré yam-yam tãab pusgo',
        'traduction':  "J'ai acheté du néré, trois mille",
        'oz_result': {
            'product':    'Néré',
            'amount':     3000,
            'type':       'ACHAT',
            'confidence': 0.91,
            'transcript': 'M kõ neré yam-yam tãab pusgo',
        },
        'whatsapp_response': {
            'VENTE': '✅ VENTE kẽenga!\nYam-yam: +{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
            'ACHAT': '✅ ACHAT kẽenga!\nYam-yam: -{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
        },
    },
    {
        'id':          'moore_05',
        'file':        'audio/fixtures/moore_05.wav',
        'langue':      'moore',
        'langue_label':'Mooré',
        'script':      'M bê sak pagen wax pisi-fo pusgo',
        'traduction':  "J'ai vendu un pagne wax, quinze mille",
        'oz_result': {
            'product':    'Pagne wax',
            'amount':     15000,
            'type':       'VENTE',
            'confidence': 0.95,
            'transcript': 'M bê sak pagen wax pisi-fo pusgo',
        },
        'whatsapp_response': {
            'VENTE': '✅ VENTE kẽenga!\nYam-yam: +{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
            'ACHAT': '✅ ACHAT kẽenga!\nYam-yam: -{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
        },
    },

    # ─── DIOULA ────────────────────────────────────────────────────────
    {
        'id':          'dioula_01',
        'file':        'audio/fixtures/dioula_01.wav',
        'langue':      'dioula',
        'langue_label':'Dioula',
        'script':      'N ye paan saba feere waga kelen-kelen waga duuru',
        'traduction':  "J'ai vendu 3 pagnes, chacun cinq mille",
        'oz_result': {
            'product':    'Pagnes',
            'amount':     15000,
            'type':       'VENTE',
            'confidence': 0.93,
            'transcript': 'N ye paan saba feere waga kelen-kelen waga duuru',
        },
        'whatsapp_response': {
            'VENTE': '✅ Feere sɛbɛra!\nWaga: +{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
            'ACHAT': '✅ San sɛbɛra!\nWaga: -{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
        },
    },
    {
        'id':          'dioula_02',
        'file':        'audio/fixtures/dioula_02.wav',
        'langue':      'dioula',
        'langue_label':'Dioula',
        'script':      'N ye sabun san waga fila',
        'traduction':  "J'ai acheté du savon, deux mille",
        'oz_result': {
            'product':    'Savon',
            'amount':     2000,
            'type':       'ACHAT',
            'confidence': 0.94,
            'transcript': 'N ye sabun san waga fila',
        },
        'whatsapp_response': {
            'VENTE': '✅ Feere sɛbɛra!\nWaga: +{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
            'ACHAT': '✅ San sɛbɛra!\nWaga: -{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
        },
    },
    {
        'id':          'dioula_03',
        'file':        'audio/fixtures/dioula_03.wav',
        'langue':      'dioula',
        'langue_label':'Dioula',
        'script':      'N ye daga feere waga keme saba',
        'traduction':  "J'ai vendu de la viande, trois cents",
        'oz_result': {
            'product':    'Viande',
            'amount':     300,
            'type':       'VENTE',
            'confidence': 0.87,
            'transcript': 'N ye daga feere waga keme saba',
        },
        'whatsapp_response': {
            'VENTE': '✅ Feere sɛbɛra!\nWaga: +{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
            'ACHAT': '✅ San sɛbɛra!\nWaga: -{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
        },
    },
    {
        'id':          'dioula_04',
        'file':        'audio/fixtures/dioula_04.wav',
        'langue':      'dioula',
        'langue_label':'Dioula',
        'script':      'N ye kɔnɔ san waga kelen',
        'traduction':  "J'ai acheté du poulet, mille francs",
        'oz_result': {
            'product':    'Poulet',
            'amount':     1000,
            'type':       'ACHAT',
            'confidence': 0.91,
            'transcript': 'N ye kɔnɔ san waga kelen',
        },
        'whatsapp_response': {
            'VENTE': '✅ Feere sɛbɛra!\nWaga: +{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
            'ACHAT': '✅ San sɛbɛra!\nWaga: -{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
        },
    },
    {
        'id':          'dioula_05',
        'file':        'audio/fixtures/dioula_05.wav',
        'langue':      'dioula',
        'langue_label':'Dioula',
        'script':      'N ye fini feere waga tan',
        'traduction':  "J'ai vendu du tissu, dix mille",
        'oz_result': {
            'product':    'Tissu',
            'amount':     10000,
            'type':       'VENTE',
            'confidence': 0.93,
            'transcript': 'N ye fini feere waga tan',
        },
        'whatsapp_response': {
            'VENTE': '✅ Feere sɛbɛra!\nWaga: +{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
            'ACHAT': '✅ San sɛbɛra!\nWaga: -{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
        },
    },
]

# Index par ID pour accès rapide
FIXTURES_BY_ID = {f['id']: f for f in AUDIO_FIXTURES}

# Réponses WhatsApp par langue (pour les nouveaux messages texte)
WHATSAPP_RESPONSES = {
    'moore': {
        'VENTE': '✅ VENTE kẽenga!\nYam-yam: +{amount} FCFA\nMosgu: {product}\nFo score: {score}/100\n\nTaas /bilan n tõnd fo bilãan.',
        'ACHAT': '✅ ACHAT kẽenga!\nYam-yam: -{amount} FCFA\nMosgu: {product}\nFo score: {score}/100',
        'AIDE':  '🤖 FasoBazar IA\n\n/bilan → fo bilãan\n/score → fo score\n/aide → sõor kãan\n\nKõ vocal tõnd fo vente walla achat!',
        'BILAN': '📊 Fo bilãan:\nVente: +{ventes} FCFA\nAchat: -{achats} FCFA\nBénéfice: {benefice} FCFA',
        'SCORE': '⭐ Fo score: {score}/100\nStatus: {status}\n{"✅ Fo credit eligible!" if eligible else "📈 Kõ transactions fo score wã."}',
        'INCONNU': 'M pa wʋmame. Tõnd vocal walla taas: VENTE Pagn 15000',
    },
    'dioula': {
        'VENTE': '✅ Feere sɛbɛra!\nWaga: +{amount} FCFA\nFɛn: {product}\nI score: {score}/100\n\nSɛbɛ /bilan k\'i jate.',
        'ACHAT': '✅ San sɛbɛra!\nWaga: -{amount} FCFA\nFɛn: {product}\nI score: {score}/100',
        'AIDE':  '🤖 FasoBazar IA\n\n/bilan → i tile jate\n/score → i score\n/aide → dɛmɛ\n\nTi vocal k\'i feere walla san!',
        'BILAN': '📊 I tile jate:\nFeere: +{ventes} FCFA\nSan: -{achats} FCFA\nNafa: {benefice} FCFA',
        'SCORE': '⭐ I score: {score}/100\nStatus: {status}\n{"✅ I credit lɔn!" if eligible else "📈 A feere ɲɔgɔn k\'i score ca."}',
        'INCONNU': 'N ma fara. Ti vocal walla sɛbɛ: VENTE Fini 10000',
    },
    'fr': {
        'VENTE': '✅ Vente enregistrée!\nMontant: +{amount} FCFA\nProduit: {product}\nScore: {score}/100',
        'ACHAT': '✅ Achat enregistré!\nMontant: -{amount} FCFA\nProduit: {product}\nScore: {score}/100',
        'AIDE':  '🤖 FasoBazar IA\n\n/bilan → résumé du jour\n/score → ton score\n/aide → cette aide\n\nEnvoie une note vocale pour enregistrer!',
        'BILAN': '📊 Bilan du jour:\nVentes: +{ventes} FCFA\nAchats: -{achats} FCFA\nBénéfice: {benefice} FCFA',
        'SCORE': '⭐ Score: {score}/100\nStatut: {status}\n{"✅ Éligible au crédit!" if eligible else "📈 Continue à enregistrer!"}',
        'INCONNU': 'Je n\'ai pas compris. Essaie une note vocale ou tape: VENTE Pagnes 15000',
    },
}

def get_whatsapp_response(langue: str, action: str, **kwargs) -> str:
    """
    Retourne le message WhatsApp dans la langue du trader.
    action: 'VENTE' | 'ACHAT' | 'AIDE' | 'BILAN' | 'SCORE' | 'INCONNU'
    kwargs: amount, product, score, ventes, achats, benefice, status, eligible
    """
    lang_responses = WHATSAPP_RESPONSES.get(langue, WHATSAPP_RESPONSES['fr'])
    template = lang_responses.get(action, lang_responses['INCONNU'])
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template