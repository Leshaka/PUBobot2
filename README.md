# PUBobot2
**PUBobot2** is a Discord bot for pickup games organisation. PUBobot2 have a remarkable list of features such as rating matches, rank roles, drafts, map votepolls and more!

### Some screenshots
![screenshots](https://cdn.discordapp.com/attachments/824935426228748298/836978698321395712/screenshots.png)

### Using the public bot instance
If you want to test the bot, feel free to join [**Pubobot2-dev** discord server](https://discord.gg/rjNt9nC).  
All the bot settings can be found and configured on the [Web interface](https://pubobot.leshaka.xyz/).  
For the complete list of commands see [COMMANDS.md](https://github.com/Leshaka/PUBobot2/blob/main/COMMANDS.md).  
You can invite the bot to your discord server from the [web interface](https://pubobot.leshaka.xyz/) or use the direct [invite link](https://discord.com/oauth2/authorize?client_id=177021948935667713&scope=bot).

### Support
Hosting the service for everyone is not free, not mentioning the actual time and effort to develop the project. If you enjoy the bot please subscribe on [Boosty](https://boosty.to/leshaka).

## Hosting the bot yourself

### Requirements
* **Python 3.9+** 
* **MySQL**.
* **gettext** for multilanguage support.

### Installing
* Create mysql user and database for PUBobot2:
* * `sudo mysql`
* * `CREATE USER 'pubobot'@'localhost' IDENTIFIED BY 'your-password';`
* * `CREATE DATABASE pubodb CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;`
* * `GRANT ALL PRIVILEGES ON pubodb.* TO 'pubobot'@'localhost';`
* Install required modules and configure PUBobot2:
* * `git clone https://github.com/Leshaka/PUBobot2`
* * `cd PUBobot2`
* * `pip3 install -r requirements.txt`
* * `cp config.example.cfg config.cfg`
* * `nano config.cfg` - Fill config file with your discord bot instance credentials and mysql settings and save.
* * Optionally, if you want to use other languages, run script to compile translations: `./compile_locales.sh`.
* * `python3 PUBobot2.py` - If everything is installed correctly the bot should launch without any errors and give you CLI.

## Credits
Developer: **Leshaka**. Contact: leshkajm@ya.ru.  
Used libraries: [discord.py](https://github.com/Rapptz/discord.py), [aiomysql](https://github.com/aio-libs/aiomysql), [emoji](https://github.com/carpedm20/emoji/), [glicko2](https://github.com/deepy/glicko2), [TrueSkill](https://trueskill.org/), [prettytable](https://github.com/jazzband/prettytable).

## License
Copyright (C) 2020 **Leshaka**.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License version 3 as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

See 'GNU GPLv3.txt' for GNU General Public License.
