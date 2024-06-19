# Using gymnasium `Env` api:
# - reset to set initial state (empty schedule)
# - action_space.sample() is used to get a random action
# - step is doing an action (scheduling 1 game)
#   - step has ability to terminate (when all games are scheduled)
# - action_space and observation_space specify valid actions and observations

# can the actions be different each step?

import gymnasium as gym
from gymnasium import spaces
#import pygame
from datetime import datetime
from datetime import timedelta
import pandas as pd


class SchedulingEnv(gym.Env):
    metadata = {"render_modes": [], "render_fps": 4}

    def __init__(self, times, teams):
        self._times = times
        self._teams = teams
        self.reset()

        #score = self._score_schedule()

        # 4 possible actions:
        # - don't schedule a game at the current time
        # - the 3 possible games that could be scheduled
        #
        # XXX maybe this should be Sequence instead for a variable size space
        self.action_space = spaces.Discrete(12)
        #self.action_space = spaces.Sequence(spaces.Discrete(4))

        # XXX what should this be?
        #self.observations_space = spaces.Tuple(tuple(map(lambda time: spaces.Tuple((spaces.Text, spaces.Text)), times)))

        """
        (
            ("may 3, 20:45", ("", "")),
            ("may 3, 22:15", ("team0", "team1")),
        )"""
        #self.observations_space = spaces.Tuple(tuple(map(lambda time: spaces.Tuple((spaces.Text(16), spaces.Tuple((spaces.Text(16), spaces.Text(16))))), times)))

        """
        (
            #(d, h, team0, team1, league)
            (1, 20, 0, 1, 0),
            (2, 21, 2, 3, 0),
        )
        """
#        self.observations_space = spaces.Tuple(tuple([-1] * 5 * len(times)))
        self.observations_space = spaces.MultiDiscrete([len(times)] + ([128, 24, 7, 7, 5] * len(times))) # XXX 4 is league 6 is teams so we go 1 up for "null" value

    def _get_obs(self):
        flat = [self._index]
        for game in self._schedule:
            for item in game:
                flat.append(item)
        return flat
        #return tuple(map(lambda game: (game[0], (game[1][0], game[1][1])), self._schedule))

    def _get_info(self):
        return None # TODO: do i care about info?

    def print_schedule(self):
        for time in self._schedule:
            print(f'Day {time[0]} time {time[1]} league {time[4]}: {time[2]} - {time[3]}')

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._index = 0 # index in times array
        self._round = 0 # current round we're scheduling (out of 10)
        self.games_to_schedule = self._get_round_robin(self._round)
        first_time = self._parse_time(self._times[0])
        self._schedule = list(map(lambda time: [*self._get_init_times(time, first_time), 6, 6, 4], self._times)) # 6 to indicate no game
        return self._get_obs(), self._get_info()

    def step(self, action):
        reward = 0
        terminated = False
        truncated = False

        #print(f'step with action {action}')

        if action < len(self.games_to_schedule):
            if self.games_to_schedule[action] is None:
                # tried to scheduled games in wrong order
                # We should never get here
                print(f"tried to schedule games in wrong order!!! action: {action}")
                print(self.games_to_schedule)
                exit(2)
                reward = -99999
            else:
                # schedule a game at this time
                self._schedule[self._index][2] = self.games_to_schedule[action][0] # set team0
                self._schedule[self._index][3] = self.games_to_schedule[action][1] # set team1
                self._schedule[self._index][4] = action // 3 # set league
                self.games_to_schedule[action] = None
                #print(f'scheduled a game at index {self._index}')
                self._index += 1
        else:
            # don't schedule a game at this time
            # XXX: it seems like it's too likely to want to skip games...
            # the score doesn't penalize not enough games being scheduled!!!
            #print(f'SKIPPED a game at index {self._index}')
            #
            #update jun 3: this should never happenn!!!
            print("tried to skip opportunity to schedule game!")
            exit(3)
            reward = -9
            self._index += 1


        # handle moving on to next round
        move_on = True
        for game in self.games_to_schedule:
            if game is not None:
                move_on = False
        if move_on:
            self._round += 1
            self.games_to_schedule = self._get_round_robin(self._round)

        #handle being done
        if self._index >= len(self._times) or self._round >= 10:
            terminated = True
            reward = self._score_schedule()
            #self.print_schedule()
            print(f'schedule got score of {reward}')

        return self._get_obs(), reward, terminated, truncated, self._get_info()

    def _get_init_times(self, time_str, first_time):
        time = self._parse_time(time_str)
        delta = time - first_time
        return [delta.days, time.hour]


    def _score_schedule(self):
        """scores the schedule, for now just tries to make it spread out"""
        score = 0
        team_games = []
        for _i in range(24):
            team_games.append([])

        #print(self._schedule)
        # print(team_games)

        for game in self._schedule:
            # print(game)
            # print([game[4] * 6 + game[2]])
            if game[2] != 24:
                team_games[game[2]].append((game[0], game[1]))
            else:
                print("top 24")
            if game[3] != 24:
                team_games[game[3]].append((game[0], game[1]))
            else:
                print("bot 24")


        # print(team_games)

        # [[(4, 20), (10, 22)], ...]
        for one_teams_games in team_games:
            # print(one_teams_games)
            if len(one_teams_games) < 10:
                print("SHOULD NEVER GET HERE")
                exit(5)
                score -= 999#9999999999
            last_day = None
            number_early = 0
            for game in one_teams_games:
                if last_day != None:
                    diff = game[0] - last_day
                    score += diff ** 2
                    early = game[1] <= 21 # TODO maybe account for minutes
                    if early:
                        number_early += 1
                last_day = game[0]
            if number_early < 5:
                score -= (5 - number_early) ** 2 * 100

        return score

    def _get_round_robin(self, _round):
        # TODO: make sure this is working correctly...
        # https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm
        half = len(self._teams[0]) // 2 # might break with odd numbers
        rotated = []
        for i in range(1,len(self._teams[0])):
            rotated.append(i)
        for i in range(_round):
            rotated.append(rotated[0])
            rotated.pop(0)
        rotated.insert(0, 0)

        pairs = []
        for league in range(4):
            for i in range(0, half):
                pairs.append((rotated[i] + league * 6, rotated[-(i + 1)] + league * 6))

        return pairs

    def _parse_time(self, time):
        return datetime.strptime(time, '%m/%d/%y %H:%M')

    def schedule_to_csv(self, path=None):
        "return a csv string representing schedule"
        # Start_Date,Start_Time,End_Date,End_Time,Location,Location_URL,Event_Type,Team1_ID,Team2_ID,Team1_Name,Team2_Name
        # 05/20/2024,20:30,05/20/2024,21:45,George S. Eccles Ice Center --- Surface 1,https://www.google.com/maps?cid=12548177465055817450,Game,8387070,8387071,Chiefs,Mountain Men
        header = ["Start_Date","Start_Time","End_Date","End_Time","Location","Location_URL","Event_Type","Team1_ID","Team2_ID","Team1_Name","Team2_Name"]
        csv = []

        get_day = lambda time: time.strftime("%m/%d/%Y")
        get_time = lambda time: time.strftime("%H:%M")

        for i in range(len(self._schedule)):
            start_time = self._parse_time(self._times[i])
            end_time = start_time + timedelta(hours=1, minutes=15)
            line = [get_day(start_time), get_time(start_time), get_day(end_time), get_time(end_time)]
            line.append("ice center")
            line.append("http://example.com")
            line.append("Game")
            line.append("123")
            line.append("456")
            game = self._schedule[i]
            team0_index = game[2]
            team1_index = game[3]
            line.append(self._teams[team0_index // 6][team0_index % 6])
            line.append(self._teams[team1_index // 6][team1_index % 6])
            csv.append(line)

        df = pd.DataFrame(csv, columns=header)
        return df.to_csv(path_or_buf=path, index=False)

        """
        (
            #(d, h, team0, team1, league)
            (1, 20, 0, 1, 0),
            (2, 21, 2, 3, 0),
        )
        """
