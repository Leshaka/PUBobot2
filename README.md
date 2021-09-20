# PUBobot2

**PUBobot2** is a Discord bot for pickup games organisation.
PUBobot2 have a remarkable list of features such as rating matches,
rank roles, drafts, map votepolls and more!

### Some screenshots

![screenshots](https://cdn.discordapp.com/attachments/824935426228748298/836978698321395712/screenshots.png)

### Using the public bot instance

If you want to test the bot, feel free to join [**Pubobot2-dev** discord server](https://discord.gg/rjNt9nC).  
All the bot settings can be found and configured on the [Web interface](https://pubobot.leshaka.xyz/).  
For the complete list of commands see [COMMANDS.md](https://github.com/Leshaka/PUBobot2/blob/main/COMMANDS.md).  
You can invite the bot to your discord server from the [web interface](https://pubobot.leshaka.xyz/) or use the direct [invite link](https://discord.com/oauth2/authorize?client_id=177021948935667713&scope=bot).

### Support

Hosting the service for everyone is not free, not mentioning the actual time and effort to develop the project.
If you enjoy the bot please subscribe on [Patreon](https://patreon.com/pubobot2) or donate any amount directly on [PayPal](https://paypal.me/leshkajm).

## Hosting the bot yourself

### Known limitations

- currently web interface is missing from the source code, this is by design
- you need to create Discord app and register bot on your own - follow official docs of [discord.py](https://discordpy.readthedocs.io/en/stable/discord.html)
  but notice you man need to enable `Privileged Gateway Intents`

### Requirements

* **Python 3.9** and modules from pip, see `requirements.txt`
* **MySQL**.
* **gettext** system package for multilanguage support.
* logs are stored under `logs/` directroy, relative to the location where app is run

### Installing

Creating database, user and privileges - see example `hack/mysql/install.sql`,
and adjust it to your needs.

* Install required modules and configure PUBobot2:
* * `git clone https://github.com/Leshaka/PUBobot2`
* * `cd PUBobot2`
* * `python3.9 -m pip install -r requirements.txt`
* * `cp config.example.cfg config.cfg`
* * `nano config.cfg` - Fill config file with your discord bot instance credentials and mysql settings and save.
* * Optionally, if you want to use other languages, run script to compile translations: `./compile_locales.sh`.
* * execute `python3.9 PUBobot2.py` to start the bot.
* If everything is installed correctly the bot should launch without any errors and give you CLI.


## Development

- create config.cfg as defined in installing section
- set up MySQL instance to connect to (remeber to make database backups prior running bot)
- develop code and run it locally

### Dockerfile

If you not want to run python directly on your machine then for convenience
there is `Dockerfile` which should help you to run bot in isolated,
unprivileged container. The major drawback is that it just build app on every
run, so it is slower to start.

```bash
docker build -t mybot:dev .

docker run  -it \
  -v ${PWD}/config.cfg:/home/bot/config.cfg:ro \
  -v ${PWD}/logs:/home/bot/logs:rw \
  mybot:dev
```

### Docker Compose

If you need a fully workigng setup with MySQL then use docker compose.

```bash
docker-compose up --build

```

## Credits

Developer: **Leshaka**. Contact: leshkajm@ya.ru.
Used libraries:
- [aiomysql](https://github.com/aio-libs/aiomysql)
- [discord.py](https://github.com/Rapptz/discord.py)
- [emoji](https://github.com/carpedm20/emoji/)
- [glicko2](https://github.com/deepy/glicko2)
- [prettytable](https://github.com/jazzband/prettytable)
- [TrueSkill](https://trueskill.org/)

## License

Copyright (C) 2020 **Leshaka**.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License version 3 as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

See 'GNU GPLv3.txt' for GNU General Public License.
