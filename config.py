from os import environ

def config(app):
    '''
    Discord webhook URL to send data to. Set to None to disable plugin entirely.
    '''
    app.config['DISCORD_WEBHOOK_URL'] = environ.get('DISCORD_WEBHOOK_URL')

    '''
    Limit on number of solves for challenge to trigger webhook for. Set to None to send a message for every solve.
    '''
    # app.config['DISCORD_WEBHOOK_LIMIT'] = environ.get('DISCORD_WEBHOOK_LIMIT', '3')
    app.config['DISCORD_WEBHOOK_LIMIT'] = None

