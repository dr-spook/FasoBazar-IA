"""
FasoBazar IA — Modèles de données
3 tables : Trader, Transaction, TrustScore
"""
from django.db import models
import uuid
from django.contrib.auth.hashers import make_password, check_password


class Trader(models.Model):
    """Commerçante enregistrée"""
    LANGUAGE_CHOICES = [
        ('moore',    'Mooré'),
        ('dioula',   'Dioula'),
        ('fulfulde', 'Fulfuldé'),
        ('fr',       'Français'),
    ]
    STATUS_CHOICES = [
        ('pending',  'En attente'),
        ('active',   'Actif'),
        ('premium',  'Premium'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=200)
    phone      = models.CharField(max_length=30, unique=True)
    language   = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='moore')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    password = models.CharField(max_length=256, default='')

    class Meta:
        db_table = 'traders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def initials(self):
        parts = self.name.split()[:2]
        return ''.join(p[0].upper() for p in parts if p)


class Transaction(models.Model):
    """Journal de caisse — une entrée par vente ou achat"""
    TYPE_CHOICES = [
        ('VENTE', 'Vente'),
        ('ACHAT', 'Achat'),
    ]
    SOURCE_CHOICES = [
        ('REAL',      'Pipeline IA réel'),
        ('OZ',        'Mode Oz (simulation)'),
        ('WHATSAPP',  'WhatsApp'),
        ('WEB',       'Interface web'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trader         = models.ForeignKey(Trader, on_delete=models.CASCADE, related_name='transactions')
    product        = models.CharField(max_length=200)
    amount         = models.DecimalField(max_digits=12, decimal_places=0)  # En FCFA
    type           = models.CharField(max_length=10, choices=TYPE_CHOICES)
    raw_transcript = models.TextField(blank=True, null=True)
    source         = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='WEB')
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['trader', 'created_at']),
            models.Index(fields=['trader', 'type']),
        ]

    def __str__(self):
        sign = '+' if self.type == 'VENTE' else '-'
        return f"{self.trader.name} — {sign}{self.amount} FCFA ({self.product})"

    @property
    def amount_int(self):
        return int(self.amount)

    @property
    def amount_formatted(self):
        """Formate 15000 en '15 000'"""
        return f"{int(self.amount):,}".replace(',', ' ')


class TrustScore(models.Model):
    """Score de Confiance Alternatif (SCA) — 1:1 avec Trader"""
    STATUS_CHOICES = [
        ('EN_CONSTRUCTION', 'En construction'),
        ('ELIGIBLE',        'Éligible crédit'),
        ('CONFIRME',        'Score confirmé'),
        ('PREMIUM',         'Profil premium'),
    ]

    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trader            = models.OneToOneField(Trader, on_delete=models.CASCADE, related_name='trust_score')
    score             = models.IntegerField(default=0)
    transaction_count = models.IntegerField(default=0)
    total_revenue     = models.DecimalField(max_digits=14, decimal_places=0, default=0)
    computed_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trust_scores'

    def __str__(self):
        return f"{self.trader.name} — Score {self.score}/1000"

    @property
    def status(self):
        if self.transaction_count < 3:
            return 'EN_CONSTRUCTION'
        if self.score >= 700:
            return 'CONFIRME'
        if self.score >= 300:
            return 'ELIGIBLE'
        return 'EN_CONSTRUCTION'

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, '')

    @property
    def eligible_credit(self):
        return self.score >= 30 and self.transaction_count >= 3

    @property
    def score_color(self):
        if self.transaction_count < 3:
            return 'secondary'
        if self.score >= 700:
            return 'success'
        if self.score >= 300:
            return 'warning'
        return 'secondary'

    @property
    def score_percent(self):
        return min(100, max(0, self.score))