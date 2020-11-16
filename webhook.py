from flask import request
from werkzeug.wrappers.json import JSONMixin
from CTFd.utils.dates import ctftime
from CTFd.models import Challenges, Solves
from CTFd.utils import config as ctfd_config
from CTFd.utils.user import get_current_team, get_current_user
from discord_webhook import DiscordWebhook, DiscordEmbed
from functools import wraps
from .config import config
import re

ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
sanreg = re.compile(r'(~|!|@|#|\$|%|\^|&|\*|\(|\)|\_|\+|\`|-|=|\[|\]|;|\'|,|\.|\/|\{|\}|\||:|"|<|>|\?)')
sanitize = lambda m: sanreg.sub(r'\1',m)

def load(app):
	config(app)
	TEAMS_MODE = ctfd_config.is_teams_mode()

	if not app.config['DISCORD_WEBHOOK_URL']:
		print("No DISCORD_WEBHOOK_URL set! Plugin disabled.")
		return
	print("Loading plugin discord webhook!!")

	def challenge_attempt_decorator(f):
		@wraps(f)
		def wrapper(*args, **kwargs):
			result = f(*args, **kwargs)

			if not ctftime():
				return result

			if isinstance(result, JSONMixin):
				data = result.json
				if isinstance(data, dict) and data.get("success") == True and isinstance(data.get("data"), dict) and data.get("data").get("status") == "correct":
					if request.content_type != "application/json":
						request_data = request.form
					else:
						request_data = request.get_json()
					challenge_id = request_data.get("challenge_id")
					challenge = Challenges.query.filter_by(id=challenge_id).first_or_404()
					solvers = Solves.query.filter_by(challenge_id=challenge.id)
					if TEAMS_MODE:
						solvers = solvers.filter(Solves.team.has(hidden=False))
					else:
						solvers = solvers.filter(Solves.user.has(hidden=False))
					num_solves = solvers.count()

					limit = app.config["DISCORD_WEBHOOK_LIMIT"]
					if limit and num_solves > int(limit):
						return result
					webhook = DiscordWebhook(url=app.config['DISCORD_WEBHOOK_URL'])

					user = get_current_user()
					difficulty = challenge.tags[0].value
					color = 0x0

					if (difficulty == 'Easy'):
						color = 0x0EEC88
					elif (difficulty == 'Medium'):
						color = 0xfb901e
					elif (difficulty == 'Hard'):
						color = 0xff2856
					elif (difficulty == 'Warmup'):
						color = 0x00fff9
					else:
						color = 0x00fff9

					emoji = ''
					if num_solves == 1:
						fb_embed = DiscordEmbed(title='FIRST BLOOD!', description=f'**{sanitize(user.name)}** just got first blood on the **{difficulty}** difficulty **{sanitize(challenge.category)}** challenge **{sanitize(challenge.name)}**!', color=color)
						fb_embed.set_image(url='https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/twitter/259/syringe_1f489.png')
						fb_embed.set_timestamp()
						webhook.add_embed(fb_embed)
					elif num_solves == 2:
						emoji = ' 🥈'
					elif num_solves == 3:
						emoji = ' 🥉'
					embed = DiscordEmbed(title='Flag Captured!', description=f'**{sanitize(user.name)}** captured a flag!', color=color)
					embed.add_embed_field(name='User', value=sanitize(user.name))
					embed.add_embed_field(name='Challenge', value=sanitize(challenge.name))
					embed.add_embed_field(name='Category', value=sanitize(challenge.category))
					embed.add_embed_field(name='Difficulty', value=difficulty)
					embed.add_embed_field(name='Solves', value=f'{str(num_solves)}{emoji}')
					webhook.execute()
			return result
		return wrapper

	app.view_functions['api.challenges_challenge_attempt'] = challenge_attempt_decorator(app.view_functions['api.challenges_challenge_attempt'])
