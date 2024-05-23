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

class SchedulingEnv(gym.Env):
    metadata = {"render_modes": [], "render_fps": 4}

    def __init__(self, times, teams):
        self._times = times
        self._teams = teams

        # XXX: next 3 maybe not necessary becaues of reset()
        self._index = 0 # index in times array
        self._round = 0 # current round we're scheduling (out of 10)
        self._schedule = tuple(map(lambda time: (time, ""), times))

        # 4 possible actions:
        # - don't schedule a game at the current time
        # - the 3 possible games that could be scheduled
        #
        # XXX maybe this should be Sequence instead for a variable size space
        #self.action_space = spaces.Discrete(4)
        self.action_space = spaces.Sequence(spaces.Discrete(4))

        # XXX what should this be?
        #self.observations_space = spaces.Tuple(tuple(map(lambda time: spaces.Tuple((spaces.Text, spaces.Text)), times)))
        self.observations_space = spaces.Tuple(tuple(map(lambda time: spaces.Tuple((spaces.Text(16), spaces.Text(128))), times)))

    def _get_obs(self):
        return self._schedule

    def _get_info(self):
        return None # TODO: do i care about info?

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._index = 0 # index in times array
        self._round = 0 # current round we're scheduling (out of 10)
        self._schedule = tuple(map(lambda time: (time, ""), times))
        return self._get_obs(), self._get_info()

    def step(self, action):
        pass

    def _score_schedule(self):
        """scores the schedule, for now just tries to make it spread out"""
        pass

    def _get_round_robin(self, _round):
        # https://en.wikipedia.org/wiki/Round-robin_tournament#Scheduling_algorithm
        half = len(self._teams) // 2 # might break with odd numbers
        rotated = []
        for i in range(1,len(self._teams)):
            rotated.append(self._teams[i])
        for i in range(_round):
            rotated.append(rotated[0])
            rotated.pop(0)
            rotated.insert(0, self._teams[0])

        pairs = []
        for i in range(0, half):
            pairs.append((rotated[i], rotated[-(i + 1)]))

        return pairs