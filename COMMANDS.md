# Available Commands

#### Queues
| command               | description                                             |
|-----------------------|---------------------------------------------------------|
| /add                  | Join queues                                             |
| /remove               | Leave queues                                            |
| /who                  | List queue players                                      |
| /promote              | Promote a queue                                         |
| /server               | Show queue server setting                               |
| /maps                 | Show queue map list                                     |
| /map                  | Show random map from a queue map list                   |
| /auto_ready           | Confirm check-in automatically on next queue start      |
| /expire               | Show or set your current expire timer                   |

#### Matches
| command               | description                                             |
|-----------------------|---------------------------------------------------------|
| /ready                | Confirm check-in                                        |
| /notready             | Decline check-in                                        |
| /capfor               | Become a captain                                        |
| /pick                 | Pick a player                                           |
| /subme                | Request a substitute                                    |
| /subfor               | Become a substitute                                     |
| /teams                | Show current teams                                      |
| /report               | Report match result                                     |

#### Personal settings
| command               | description                                             |
|-----------------------|---------------------------------------------------------|
| /switch_dms           | Toggle DM notifications                                 |
| /expire_default       | Configure your default auto-remove behaviour            |
| /subscribe            | Subscribe to queue or channel promotion roles           |
| /unsubscribe          | Unsubscribe from queue or channel promotion roles       |
| /nick                 | Change your nick with rating prefix included            |

#### Stats
| command               | description                                             |
|-----------------------|---------------------------------------------------------|
| /leaderboard          | Show rating leaderboard                                 |
| /rank                 | Show your or another player's rating stats              |
| /lastgame             | Show last played match                                  |
| /top                  | Show top active players on the channel                  |
| /stats show           | Show overall channel stats                              |

#### Miscellaneous
| command               | description                                             |
|-----------------------|---------------------------------------------------------|
| /cointoss             | Flip a coin                                             |
| /help                 | Show channel or queue help                              |

#### Administration and Moderation
| command               | description                                             |
|-----------------------|---------------------------------------------------------|
| /channel enable       | Enable the bot this channel                             |
| /channel disable      | Disable the bot this channel                            |
| /channel show         | Show channel configuration                              |
| /channel set          | Configure a channel variable                            |
|-                      |                                                         |
| /queue create_pickup  | Create a new pickup queue                               |
| /queue list           | List all queues on the channel                          |
| /queue show           | Show queue configuration                                |
| /queue set            | Configure a queue variable                              |
| /queue delete         | Delete a queue                                          |
| /queue add_player     | Add a player to queue                                   |
| /queue remove_player  | Remove a player from all or selected queue              |
| /queue clear          | Remove all players from all or selected queue           |
| /queue start          | Manually start a queue                                  |
|-                      |                                                         |
| /match report         | Report an ongoing match result as a moderator           |
| /match create         | Manually create a rating match result                   |
| /match sub_player     | Forcefully swap one player with another                 |
| /match put            | Forcefully put a player in a team or unpicked list      |
|-                      |                                                         |
| /noadds list          | List banned players                                     |
| /noadds add           | Add a player to the ban list                            |
| /noadds remove        | Remove a player from the ban list                       |
|-                      |                                                         |
| /phrases add          | Add a player phrase on an add command                   |
| /phrases clear        | Clear player's phrases list                             |
|-                      |                                                         |
| /rating seed          | Set player rating and deviation                         |
| /rating penality      | Substract points from a player rating                   |
| /rating hide          | Hide a player from the leaderboard                      |
| /rating unhide        | Unhide a player from the leaderboard                    |
| /rating reset         | Reset channels rating data                              |
| /rating snap          | Snap players ratings to their rank minimum value        |
|-                      |                                                         |
| /stats show           | Show channel statistics                                 |
| /stats reset          | Reset all channel data except configs                   |
| /stats reset_player   | Reset a player statistics (including rating)            |
| /stats replace_player | Replace player1 with player2 in the database            |
