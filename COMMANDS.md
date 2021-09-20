# Available Commands

<br>

> #### The following typographical conventions are used to describe command arguments:
> normal text - static argument (not to be replaced).  
> `text inside block` - variable argument (to be replaced with actual value).  
> [text in brackets] - optional argument.  
> choice-1 / choice-2 - signifies either choice-1 or choice-2.  
> `@user` - guild member mention or member nick(or name) or `name@id` mask.  
> `duration` - duration time in format: '3h 2m 1s' or '03:02:01'.  

#### Configuration

| command        | arg1       | arg2          | arg3  | Description                         |
|----------------|------------|---------------|-------|-------------------------------------|
| !enable_pubobot|            |               |       | Enable bot on given channel         |
| !create_pickup | `name`     | `max_players` |       | Create a pickup                     |
| !queues        |            |               |       | List pickup queues on the channel   |
| !set           | `variable` | `value`       |       | Configure a channel variable        |
| !set_queue     | `queue`    | `variable`    | value | Configure a queue variable          |
| !cfg           |            |               |       | Show channel configuration          |
| !cfg_queue     | `queue`    |               |       | Show queue variable                 |
| !set_cfg       | `json`     |               |       | Apply json configuration to channel |
| !set_cfg_queue | `json`     |               |       | Apply json configuration to queue   |

#### Info

| command         | arg1                        | description                                                |
|-----------------|-----------------------------|------------------------------------------------------------|
| !who            | [`queue`]                   | Show people in specified queue                             |
| !rank           | [`@user`]                   | Show ranking for the specified user                        |
| !lb             | [`page #`]                  | Show the leaderboard page specified                        |
| !expire         |                             | Show your current expire timer                             |
| !default_expire |                             | Show your default autoremove settings                      |
| !matches        |                             | Show active matches on the channel                         |
| !lastgame / !lg | [`queue` / `@user`]         | Show last match played                                     |
| !stats          | [`@user`]                   | Show games played stats for channel or for specified @user |
| !top            | [day / week / month / year] | Show top players for matches played on the channel         |

#### Actions

| command          | arg1      | description                            |
|------------------|-----------|----------------------------------------|
| +queue / !add    | `queues`  | Add to specified queues                |
| ++ / !add        |           | Add to active queues                   |
| -queue / !remove |           | Remove yourself from a specified queue |
| -- / !remove     |           | Remove yourself from all queues        |
| !promote         | [`queue`] | Promote a queue                        |
| !start           | `queue`   | Force start a queue                    |

#### Moderator Actions

| command          | arg1     | arg2     | description                                     |
|------------------|----------|----------|-------------------------------------------------|
| !reset           |          |          | Remove all players from all queues              |
| !remove_player   | `@user`  |          | Remove specified user from all queues           |
| !add_player      | `queue`  | `@user`  | Add specified user to queue                     |
| !subforce        | `@user1` | `@user2` | Substitute user1 with user2 in an active match. |

#### Personal settings

| command         | arg1                    | description                                                 |
|-----------------|-------------------------|-------------------------------------------------------------|
| !expire         | `duration`              | Sets your expire timer                                      |
| !default_expire | `duration` / AFK / none | Sets your default expire timer                              |
| !ao             |                         | Switch offline immunity for active queues                   |
| !switch_dms     |                         | Toggles DMs on queue start                                  |
| !subscribe      | [`queues`]              | Subscribe to channel or specified queues promotion role     |
| !unsubscribe    | [`queues`]              | Unsubscribe from channel or specified queues promotion role |

#### Check-in

| command         | description      |
|-----------------|------------------|
| !r / !ready     | Check-in         |
| !nr / !notready | Discard check-in |

#### Draft

| command    | arg1        | arg2                   | description                           |
|------------|-------------|------------------------|---------------------------------------|
| !capfor    | `team name` |                        | Become team captain                   |
| !pick / !p | `@user`     |                        | Pick a player                         |
| !subme     |             |                        | Request a sub                         |
| !subfor    | `@user`     |                        | Sub a user                            |
| !put       | `@user`     | `team name` / unpicked | Place a user in a team as a moderator |

#### Report match

| command       | arg1       | arg2               | description                        |
|---------------|------------|--------------------|------------------------------------|
| !rl           |            |                    | Report a loss on current match     |
| !rd           |            |                    | Report a draw on current match     |
| !rc           |            |                    | Report a cancel on current match   |
| !rw           | `match ID` | `team name` / draw | Report a win/draw as moderator     |
| !cancel_match | `match ID` |                    | Cancel a match                     |

#### Stats and Ratings managment

| command              | arg1       | arg2     | arg3          | description                                           |
|----------------------|------------|----------|---------------|-------------------------------------------------------|
| !rating_set/!seed    | `@user`    | `rating` | [`deviation`] | Set a player's rating                                 |
| !rating_hide         | `@user`    |          |               | Hide a users rating                                   |
| !rating_unhide       | `@user`    |          |               | Show a users rating                                   |
| !rating_snap         |            |          |               | Decrease all players ratings until their nearest rank |
| !rating_reset        |            |          |               | Reset the rating of all players                       |
| !undo_match          | `match ID` |          |               | Undo a match                                          |
| !stats_reset         |            |          |               | Reset all channel statistics                          |
| !stats_reset_player  | `@user`    |          |               | Reset all stats for @user                             |
| !stats_replace_player| `@user1`   | `@user2` |               | Replace @user1 with @user2 in database                |

#### Bans and Phrases

| command        | arg1      | arg2       | arg3       | description                                             |
|----------------|-----------|------------|------------|---------------------------------------------------------|
| !noadd         | `@user`   | `duration` | [`reason`] | Ban user                                                |
| !forgive       | `@user`   |            |            | Unban user                                              |
| !noadds        |           |            |            | Show active bans                                        |
| !phrases_add   | `@user`   | `phrase`   |            | Add a custom phrase to pick from on user !add command   |
| !phrases_clear | [`@user`] |            |            | Clear all phrases on the channel or for specified @user |

#### Miscellaneous

| command         | var1            | description                            |
|-----------------|-----------------|----------------------------------------|
| !server / !ip   | `queue`         | Show server string for specified queue |
| !cointoss / !ct | [heads / tails] | Flip a cointoss                        |
| !maps           | `queue`         | Show list of maps for specified queue  |
| !map            | `queue`         | Show a random map for specified queue  |
| !help           | `queue`         | Show queue description                 |
