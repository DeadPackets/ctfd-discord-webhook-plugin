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
						emoji = '🥇'
					elif num_solves == 2:
						emoji = '🥈'
					elif num_solves == 3:
						emoji = '🥉'
					else:
						emoji = '🚩'

					if num_solves == 1:
						fb_webhook = DiscordWebhook(url=app.config['DISCORD_WEBHOOK_URL'])
						fb_embed = DiscordEmbed(description=f'```md\n🩸 First blood on the [ {difficulty} ]( {challenge.category.replace("", "_")} ) challenge <{challenge.name.replace("", "_")}> goes to < {user.name.replace("", "_")} >```', color=color)
						fb_webhook.add_embed(fb_embed)
						fb_webhook.execute()
					else:
						webhook = DiscordWebhook(url=app.config['DISCORD_WEBHOOK_URL'])
						embed = DiscordEmbed(description=f'```md\n{emoji} Flag captured from the [ {difficulty} ]( {challenge.category.replace("", "_")} ) challenge <{challenge.name.replace("", "_")}> by < {user.name.replace("", "_")} > -- ({num_solves} solves)```', color=color)
						webhook.add_embed(embed)
						webhook.execute()
			return result
		return wrapper

	app.view_functions['api.challenges_challenge_attempt'] = challenge_attempt_decorator(app.view_functions['api.challenges_challenge_attempt'])
