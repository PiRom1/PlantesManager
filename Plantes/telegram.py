"""
Envoi de messages Telegram depuis l'application.

Le bot est créé une fois pour toutes avec BotFather ; son token et
l'identifiant de la conversation destinataire viennent du .env
(voir .env_example).

Usage depuis le shell :

    from Plantes.telegram import TelegramBot
    TelegramBot().send_message('Bonjour depuis PlantesManager')
"""

import logging
import os

import requests


logger = logging.getLogger(__name__)

API_URL = 'https://api.telegram.org'
TIMEOUT_SECONDS = 15


class TelegramBot:
    """
    Un bot Telegram qui écrit dans une seule conversation.

    Telegram peut répondre 200 avec `ok: false` (token révoqué, chat inconnu),
    donc on lit le corps de la réponse et pas seulement le code HTTP.
    """

    def __init__(self, token=None, chat_id=None):

        self.token = token or os.environ.get('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = chat_id or os.environ.get('TELEGRAM_CHAT_ID', '')

    @property
    def is_configured(self):
        """Token et conversation renseignés ? Sinon, aucun envoi n'est tenté."""

        return bool(self.token and self.chat_id)

    def send_message(self, text: str) -> bool:
        """
        Envoie `text` dans la conversation configurée.
        Retourne True si Telegram a accepté le message, False sinon.
        """

        if not self.is_configured:
            logger.warning('Telegram non configuré : TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID manquant')
            return False

        url = f'{API_URL}/bot{self.token}/sendMessage'
        data = {'chat_id': self.chat_id, 'text': text, 'disable_web_page_preview': True}

        try:
            response = requests.post(url, data=data, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as error:
            logger.error('Telegram injoignable : %s', type(error).__name__)
            return False

        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if response.status_code != 200 or not payload.get('ok', False):
            logger.error('Telegram a refusé le message (HTTP %s) : %s',
                         response.status_code, payload.get('description', 'sans détail'))
            return False

        logger.info('Message Telegram envoyé (%s caractères)', len(text))
        return True
