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
| command          | arg1     | arg2        | arg3  | Description                         |
|------------------|----------|-------------|-------|-------------------------------------|
| !queues          |          |             |       | List pickup queues on the channel   |
| !set_channel_cfg | `json`     |             |       | Apply json configuration to channel |
| !set_queue_cfg   | `json`     |             |       | Apply json configuration to queue   |

#### Info
| command         | arg1                  | description                                               |
|-----------------|-----------------------|-----------------------------------------------------------|
| !who            | [`queue`]               | Show people in specified queue                            |
| !rank           | [`@user`]               | Show ranking for the specified user                       |
| !lb             | [`page #`]              | Show the leaderboard page specified                       |
| !expire         |                       | Show your current expire timer                            |
| !matches        |                       | Show active matches on the channel                        |
| !lastgame / !lg | [`queue` / `@user`]         | Show last match played                                    |

#### Actions
| command          | arg1    | description                            |
|------------------|---------|----------------------------------------|
| +queue / !add    | `queues`  | Add to specified queues                |
| ++ / !add        |         | Add to active queues                   |
| -queue / !remove |         | Remove yourself from a specified queue |
| -- / !remove     |         | Remove yourself from all queues        |
| !promote         | [`queue`] | Promote a queue                        |

#### Personal settings
| command           | arg1                    | description                                                 |
|-------------------|-------------------------|-------------------------------------------------------------|
| !expire           | `duration`              | Sets your current expire timer                              |
| !ao               |                         | Switch offline immunity for active queues                   |
| !ar / !auto_ready | [`duration`]            | Confirm next match check-in automatically                   |

#### Check-in
| command         | description      |
|-----------------|------------------|
| !r / !ready     | Check-in         |
| !nr / !notready | Discard check-in |

#### Draft
| command    | arg1        | arg2                   | arg3         | description                     |
|------------|-------------|------------------------|--------------|---------------------------------|
| !capfor    | `team name` |                        |              | Become team captain             |
| !capme     |             |                        |              | Allow someone else to become the captain |
| !pick / !p | `@user`     |                        |              | Pick a player                   |
| !subme     |             |                        |              | Request a sub                   |
| !subfor    | `@user`     |                        |              | Sub a user                      |

#### Report match
| command        | arg1       | arg2               | arg3      | description                      |
|----------------|------------|--------------------|-----------|----------------------------------|
| !rl            |            |                    |           | Report a loss on current match   |
| !rd            |            |                    |           | Report a draw on current match   |
| !rc            |            |                    |           | Report a cancel on current match |
| !rw            | `match ID` | `team name` / draw |           | Report a win/draw as moderator   |
| !cancel_match  | `match ID` |                    |           | Cancel a match                   |

#### Stats and Ratings managment
| command               | arg1       | arg2   | arg3      | description                                 |
|-----------------------|------------|--------|-----------|---------------------------------------------|
| !rating_hide_player   | `@user`    |          |               | Hide a users rating                   |
| !rating_unhide_player | `@user`    |          |               | Show a users rating                   |
| !stats_reset_player   | `@user`    |          |               | Reset all stats for @user             |
| !stats_replace_player | `@user1`   | `@user2` |               | Replace @user1 with @user2 in database|
