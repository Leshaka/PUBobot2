## Avaible commands:
#### Configuration
| command        | var1     | var2        | var3  | Description                         |
|----------------|----------|-------------|-------|-------------------------------------|
| !create_pickup | name     | max_players |       | Create a pickup                     |
| !queues        |          |             |       | List pickup queues on the channel   |
| !set           | variable | value       |       | Configure a channel variable        |
| !set_queue     | queue    | variable    | value | Configure a queue variable          |
| !cfg           |          |             |       | Show channel configuration          |
| !cfg_queue     | queue    |             |       | Show queue variable                 |
| !set_cfg       | json     |             |       | Apply json configuration to channel |
| !set_cfg_queue | json     |             |       | Apply json configuration to queue   |

#### Info
| command         | var1                  | description                                               |
|-----------------|-----------------------|-----------------------------------------------------------|
| !who            | [queue]               | Show people in specified queue                            |
| !rank           | [@user]               | Show ranking for the specified user                       |
| !lb             | [page #]              | Show the leaderboard page specified                       |
| !expire         |                       | Show your current expire timer                            |
| !default_expire |                       | Show your default autoremove settings                     |
| !matches        |                       | Show active matches on the channel                        |
| !lastgame / !lg | [queue or @user]      | Show last match played                                    |
| !stats          | [@user]               | Show games played stats on channel or for specified @user |
| !top            | [day/week/month/year] | Show top players for matches played on the channel        |

#### Actions
| command          | var1    | description                            |
|------------------|---------|----------------------------------------|
| +queue / !add    | queues  | Add to specified queues                |
| ++ / !add        |         | Add to active queues                   |
| -queue / !remove |         | Remove yourself from a specified queue |
| -- / !remove     |         | Remove yourself from all queues        |
| !promote         | [queue] | Promote a queue                        |
| !start           | queue   | Force start a queue                    |
| !reset           |         | Remove all players from all queues     |

#### Personal settings
| command         | var1              | description                                                 |
|-----------------|-------------------|-------------------------------------------------------------|
| !expire         | duration          | Sets your expire timer                                      |
| !default_expire | duration/AFK/none | Sets your default expire timer                              |
| !ao             |                   | Switch offline immunity for active queues                   |
| !switch_dms     |                   | Toggles DMs on queue start                                  |
| !subscribe      | [queues]          | Subscribe to channel or specified queues promotion role     |
| !unsubscribe    | [queues]          | Unsubscribe from channel or specified queues promotion role |

#### Check-in
| command         | description      |
|-----------------|------------------|
| !r / !ready     | Check-in         |
| !nr / !notready | Discard check-in |

#### Draft
| command    | var1      | var2               | description                     |
|------------|-----------|--------------------|---------------------------------|
| !capfor    | team name |                    | Become team captain             |
| !pick / !p | @user     |                    | Pick a player                   |
| !subme     |           |                    | Request a sub                   |
| !subfor    | @user     |                    | Sub a user                      |
| !put       | @user     | team_name/unpicked | Place a user in a team as admin |

#### Report match
| command       | var1     | var2           | description                    |
|---------------|----------|----------------|--------------------------------|
| !rl           |          |                | Report a loss on current match |
| !rd           |          |                | Report a draw on current match |
| !rw           | match ID | team_name/draw | Report a win/draw as admin     |
| !cancel_match | match ID |                | Cancel a match                 |

#### Stats and Ratings managment
| command              | var1     | var2   | var3      | description                           |
|----------------------|----------|--------|-----------|---------------------------------------|
| !rating_set/!seed    | @user    | rating | deviation | Set a player's rating                 |
| !rating_hide         | @user    |        |           | Hide a users rating                   |
| !rating_unhide       | @user    |        |           | Show a users rating                   |
| !rating_reset        |          |        |           | Reset the rating of all players       |
| !undo_match          | match ID |        |           | Undo a match                          |
| !stats_reset         |          |        |           | Reset all channel statistics          |
| !stats_reset_player  | @user    |        |           | Reset all stats for @user             |
| !stats_replace_player| @user1   | @user2 |           | Replace @user1 with @user2 in database|
| !undo_match          | match ID |        |           | Undo a match                          |

#### Miscellaneous
| command         | var1          | description                            |
|-----------------|---------------|----------------------------------------|
| !server / !ip   | queue         | Show server string for specified queue |
| !cointoss / !ct | [heads/tails] | Flip a cointoss                        |
