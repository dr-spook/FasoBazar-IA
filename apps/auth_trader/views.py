"""
FasoBazar IA — Authentification commerçante
Système simple : numéro de téléphone + mot de passe
Session Django pour maintenir la connexion
"""
import logging
from django.shortcuts import render, redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages

from apps.core.models import Trader
from apps.core.services import refresh_trust_score

logger = logging.getLogger(__name__)

SESSION_KEY = 'trader_id'

# ─── Helpers de session ────────────────────────────────────────────────────

def get_logged_trader(request) -> Trader | None:
    """Retourne le Trader connecté ou None."""
    trader_id = request.session.get(SESSION_KEY)
    if not trader_id:
        return None
    try:
        return Trader.objects.get(id=trader_id)
    except Trader.DoesNotExist:
        request.session.flush()
        return None


def login_required_trader(view_func):
    """Décorateur : redirige vers /login/ si non connecté."""
    def wrapper(request, *args, **kwargs):
        if not get_logged_trader(request):
            return redirect('trader-login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Vue : Splash screen ───────────────────────────────────────────────────

class SplashView(View):
    """
    Splash screen 2 secondes → redirige selon l'état de connexion :
    - Connecté   → /app/ (directement dans l'app)
    - Non connecté → /login/
    """
    def get(self, request):
        trader = get_logged_trader(request)
        return render(request, 'auth/splash.html', {
            'redirect_url': '/app/' if trader else '/login/',
        })


# ─── Vue : Login ───────────────────────────────────────────────────────────

class LoginView(View):
    def get(self, request):
        # Déjà connecté → aller dans l'app
        if get_logged_trader(request):
            return redirect('home')
        return render(request, 'auth/login.html')

    def post(self, request):
        phone    = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        if not phone or not password:
            return render(request, 'auth/login.html', {
                'error': 'Numéro et mot de passe requis.'
            })

        # Normaliser le numéro (accepter avec ou sans +226)
        phone = _normalize_phone(phone)

        try:
            trader = Trader.objects.get(phone=phone)
        except Trader.DoesNotExist:
            return render(request, 'auth/login.html', {
                'error': 'Numéro non trouvé. Vérifie ton numéro.',
                'phone': phone,
            })

        if not trader.check_password(password):
            return render(request, 'auth/login.html', {
                'error': 'Mot de passe incorrect.',
                'phone': phone,
            })

        # Connexion réussie
        request.session[SESSION_KEY] = str(trader.id)
        request.session.set_expiry(0)  # Session jusqu'à fermeture du navigateur

        # "Se souvenir de moi" → 30 jours
        if request.POST.get('remember'):
            request.session.set_expiry(30 * 24 * 3600)

        logger.info(f'[AUTH] Login: {trader.name} ({trader.phone})')
        return redirect('home')


# ─── Vue : Inscription ─────────────────────────────────────────────────────

class RegisterView(View):
    def get(self, request):
        if get_logged_trader(request):
            return redirect('home')
        return render(request, 'auth/register.html')

    def post(self, request):
        name     = request.POST.get('name', '').strip()
        phone    = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        language = request.POST.get('language', 'moore')

        # Validation basique
        errors = {}
        if not name or len(name) < 2:
            errors['name'] = 'Nom requis (minimum 2 caractères)'
        if not phone:
            errors['phone'] = 'Numéro de téléphone requis'
        if not password or len(password) < 4:
            errors['password'] = 'Mot de passe requis (minimum 4 chiffres)'

        phone = _normalize_phone(phone)

        if Trader.objects.filter(phone=phone).exists():
            errors['phone'] = 'Ce numéro est déjà enregistré. Connecte-toi.'

        if errors:
            return render(request, 'auth/register.html', {
                'errors': errors,
                'name': name,
                'phone': request.POST.get('phone', ''),
                'language': language,
            })

        # Créer le compte
        trader = Trader(name=name, phone=phone, language=language)
        trader.set_password(password)
        trader.save()
        refresh_trust_score(trader)

        # Connecter automatiquement
        request.session[SESSION_KEY] = str(trader.id)
        request.session.set_expiry(30 * 24 * 3600)

        logger.info(f'[AUTH] Inscription: {trader.name} ({trader.phone})')
        return redirect('home')


# ─── Vue : Logout ──────────────────────────────────────────────────────────

class LogoutView(View):
    def get(self, request):
        trader = get_logged_trader(request)
        if trader:
            logger.info(f'[AUTH] Logout: {trader.name}')
        request.session.flush()
        return redirect('trader-login')


# ─── Helper : normaliser le numéro ─────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """
    Accepte : 70000001 / 0070000001 / +22670000001 / 22670000001
    Retourne toujours : +22670000001
    """
    phone = phone.replace(' ', '').replace('-', '').replace('.', '')
    if phone.startswith('+'):
        return phone
    if phone.startswith('00'):
        return '+' + phone[2:]
    if phone.startswith('226'):
        return '+' + phone
    # Numéro local burkinabè (8 chiffres)
    if len(phone) == 8:
        return '+226' + phone
    return phone