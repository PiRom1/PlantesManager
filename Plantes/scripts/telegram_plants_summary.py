from Plantes.models import User
from Plantes.telegram import TelegramBot
from Plantes.bot_scripts.plants_summary import summarize_plants



def run():

    user = User.objects.get(username='romain')
    bot = TelegramBot()
    bot.send_message(summarize_plants(user), parse_mode='HTML')