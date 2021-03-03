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
| command         | var1            | description                                                       |
|-----------------|-----------------|-------------------------------------------------------------------|
| !who            | queue name      | Shows people in specified queue                                   |
| !rank           | @user           | Shows ranking for the specified user                              |
| !lb             | page #          | Shows the leaderboard page specified                              |
| !expire         |                 | Shows your current expire timer(or sets it to specified time)     |
| !default_expire |                 | Shows default timer for the channel(or sets it to specified time) |
| !matches        |                 | Shows currently active matches on the channel                     |

#### Actions
| command              | var1  | description                            |
|----------------------|-------|----------------------------------------|
| +queue/!add queue    | queue | Add to specified queue                 |
| ++/!add              |       | Add to active queues                   |
| -queue/!remove queue | queue | Remove yourself from a specified queue |
| --/!remove           |       | Remove yourself from all queues        |
| !promote             | queue | Promote a queue                        |
| !start               | queue | Force start a queue(admin only)        |

#### Personal settings
| command         | var1              | description                               |
|-----------------|-------------------|-------------------------------------------|
| !expire         | duration          | Sets your expire timer                    |
| !default_expire | duration/AFK/none | Sets your default expire timer            |
| !ao             |                   | Switch offline immunity for active queues |
| !switch_dms     |                   | Toggles DMs on queue start                |

#### Check-in
| command       | description      |
|---------------|------------------|
| !r/!ready     | Check-in         |
| !nr/!notready | Discard check-in |

#### Draft
| command | var1      | var2               | description                     |
|---------|-----------|--------------------|---------------------------------|
| !capfor | team name |                    | Become team captain             |
| !pick   | @user     |                    | Pick a player                   |
| !subme  |           |                    | Request a sub                   |
| !subfor | @user     |                    | Sub a user                      |
| !put    | @user     | team name/unpicked | Place a user in a team as admin |

#### Report match
| command       | var1     | var2           | description                    |
|---------------|----------|----------------|--------------------------------|
| !rl           |          |                | Report a loss on current match |
| !rd           |          |                | Report a draw on current match |
| !rw           | match ID | team name/draw | Report a win/draw as admin     |
| !cancel_match | match ID |                | Cancel a match                 |

#### Ratings managment
| command           | var1     | var2   | var3      | description                     |
|-------------------|----------|--------|-----------|---------------------------------|
| !rating_set/!seed | @user    | rating | deviation | Set a player's rating           |
| !rating_hide      | @user    |        |           | Hide a users rating             |
| !rating_unhide    | @user    |        |           | Show a users rating             |
| !rating_reset     |          |        |           | Reset the rating of all players |
| !undo_match       | match ID |        |           | Undo a match                    |
