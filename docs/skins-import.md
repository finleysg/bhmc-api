# Wednesday Individual Skins Import
The objective of the importer is to import skins results in two steps:
1. Generate a simple .csv file of all winners
2. Import skins rows from that .csv file

The class that does the import work should have two primary public methods: one to generate and return the csv data and one to import the csv data as a file and create skins records. The import process should be fully idempotent.

The inport process will take an Event parameter as well as the csv data to import.

The source file for skins import is a leaderboard export from Golf Genius.

On Wednesday nights, that file will contain the following skins results:
- East gross skins
- East net skins
- North gross skins
- North net skins
- West gross skins
- West net skins

The sheets with the results can be identified by looking at the name. Skins results start with "gross skins" or "net skins" and have the course name also in the sheet name. For example: "grost skins - west", or "gross skins - north gros...".

The .csv file we generate will have the following columns:
- player name (first and last)
- player ghin (pulled from the player record after looking up by first and last name)
- course (east, north, or west)
- hole number (parsed from the detail column in the source sheets)
- skin type (gross or net)
- value (the amount the skin is worth, aka "purse")
- details (text such as "Birdie on 3 in Flight 1")

The source file will have the following columns on the skins results sheet:
- Player: the first and last name of the player
- Skins: the number of skins won
- Purse: the total value of all skins won
- Details: a comma separated list of how the skins were won. Examples: "Birdie on 7", "Eagle on 9", "Birdie on 4, Par on 7".

The results in the skins results sheets are also grouped by flight. The row header for each flight typically reads "Flight 1" or "Flight 2" and so on.

This is an example of a result sheet:
| **Flight 1**                        |           |           |                       |
| ----------------------------------- | --------- | --------- | --------------------- |
| **Player**                          | **Skins** | **Purse** | **Details**           |
| Yarri Bryn                          | 1         | $38.00    | Birdie on 7           |
| Mac Tobin                           | 1         | $38.00    | Eagle on 9            |
| Branden Lee                         | 1         | $38.00    | Birdie on 4           |
|                                     |           |           |                       |
| **Flight 2**                        |           |           |                       |
| **Player**                          | **Skins** | **Purse** | **Details**           |
| Steve Puffer                        | 2         | $34.00    | Birdie on 4, Par on 7 |
| Paul Hadden                         | 1         | $17.00    | Birdie on 9           |
| Travis Rootes                       | 1         | $17.00    | Birdie on 2           |
|                                     |           |           |                       |
| **Flight 3**                        |           |           |                       |
| **Player**                          | **Skins** | **Purse** | **Details**           |
| Rob Kinsey                          | 1         | $10.00    | Par on 2              |
| John Winn                           | 1         | $10.00    | Birdie on 4           |
| Jeff Ammann                         | 1         | $10.00    | Par on 6              |
|                                     |           |           |                       |

When a player wins more than one skin, the generated csv file should include one row per skin won. The purse column in the source sheet is a combination of all skins won, so in this case we output only the value of an individual skin.

If a player is not found in the database, still include the player name, but leave the ghin column blank.

See the /files/BHMC LG_LN 2025-05-14 Leaderboard.xls document for a representative example of a Wednesday night leaderboard file.