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
        self.action_space = spaces.Discrete(4)
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
            #(d, h, m, team0, team1)
            (1, 20, 15, 0, 1),
            (2, 21, 15, 2, 3),
        )
        """
#        self.observations_space = spaces.Tuple(tuple([-1] * 5 * len(times)))
        self.observations_space = spaces.MultiDiscrete([len(times)] + ([128, 24, len(teams) + 1, len(teams) + 1] * len(times)))

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
            print(f'Day {time[0]} time {time[1]}: {time[2]} - {time[3]}')

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._index = 0 # index in times array
        self._round = 0 # current round we're scheduling (out of 10)
        self._games_to_schedule = self._get_round_robin(self._round)
        first_time = self._parse_time(self._times[0])
        self._schedule = list(map(lambda time: [*self._get_init_times(time, first_time), len(self._teams), len(self._teams)], self._times))
        return self._get_obs(), self._get_info()

    def step(self, action):
        reward = 0
        terminated = False
        truncated = False

        if action < len(self._games_to_schedule):
            if self._games_to_schedule[action] is None:
                # tried to scheduled games in wrong order
                reward = -99999
            else:
                # schedule a game at this time
                self._schedule[self._index][2] = self._games_to_schedule[action][0] # set team0
                self._schedule[self._index][3] = self._games_to_schedule[action][1] # set team1
                self._index += 1
        else:
            # don't schedule a game at this time
            self._index += 1

        # handle moving on to next round
        move_on = True
        for game in self._games_to_schedule:
            if game is not None:
                move_on = False
        if move_on:
            self._round += 1
            self._games_to_schedule = self._get_round_robin(self._round)

        #handle being done
        if self._index >= len(self._times):
            terminated = True
            reward = self._score_schedule()

        return self._get_obs(), reward, terminated, truncated, self._get_info()

    def _get_init_times(self, time_str, first_time):
        time = self._parse_time(time_str)
        delta = time - first_time
        return [delta.days, time.hour]


    def _score_schedule(self):
        """scores the schedule, for now just tries to make it spread out"""
        score = 0
        team_games = [[]] * len(self._teams)

        for game in self._schedule:
            if game[2] != len(self._teams):
                team_games[game[2]].append((game[0], game[1]))
            if game[3] != len(self._teams):
                team_games[game[3]].append((game[0], game[1]))

        # [[(4, 20), (10, 22)], ...]
        for one_teams_games in team_games:
            last_day = None
            for game in one_teams_games:
                if last_day != None:
                    diff = game[0] - last_day
                    score += diff ** 2
                last_day = game[0]

        return score

    def _get_round_robin(self, _round):
        # https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm
        half = len(self._teams) // 2 # might break with odd numbers
        rotated = []
        for i in range(1,len(self._teams)):
            rotated.append(i)
        for i in range(_round):
            rotated.append(rotated[0])
            rotated.pop(0)
        rotated.insert(0, 0)

        pairs = []
        for i in range(0, half):
            pairs.append((rotated[i], rotated[-(i + 1)]))

        return pairs

    def _parse_time(self, time):
        return datetime.strptime(time, '%m/%d/%y %H:%M')
