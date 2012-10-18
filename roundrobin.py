import itertools
from operator import attrgetter

import playerlist
import match

class ScoreTally:

    def __init__(self, num_players):
        self.finishes = [0] * num_players
        self.mscore = 0
        self.sscore = 0
        self.swins = 0
        self.replays = 0

class Group:

    def __init__(self, num, tie, players, threshold=1):
        self._num = num
        self._players = players
        self._tie = tie
        self._threshold = threshold
        self.make_match_list()

    def make_match_list(self):
        combs = itertools.combinations(self._players, 2)
        self._matches = [match.Match(self._num, a[0], a[1]) for a in combs]

    def get_match(self, matches, player_a, player_b):
        fits = lambda m: (m.player_a == player_a and m.player_b == player_b) or\
                         (m.player_b == player_a and m.player_a == player_b) 
        gen = (match for match in matches if fits(match))
        return next(gen)

    def get_player(self, name):
        fits = lambda p: p.name.lower() == name.lower()
        gen = (player for player in self._players if fits(player))
        return next(gen)

    def compute(self):
        N = 100000

        self.tally = dict()
        for p in self._players:
            self.tally[p] = ScoreTally(len(self._players))

        for i in range(0,N):
            table = self.simulate()
            for i in range(0,len(table)):
                t = self.tally[table[i]]
                t.finishes[i] += 1./N
                t.mscore += float(table[i].mscore)/N
                t.sscore += float(table[i].sscore)/N
                t.swins += float(table[i].swins)/N
                if table[i].replayed:
                    t.replays += 1./N

    def simulate(self):
        for player in self._players:
            player.mscore = 0
            player.sscore = 0
            player.swins = 0
            player.replayed = False

        for match in self._matches:
            res = match.get_random_result()
            match.player_a.sscore += res[0] - res[1]
            match.player_a.swins += res[0]
            match.player_b.sscore += res[1] - res[0]
            match.player_b.swins += res[1]
            if res[0] > res[1]:
                match.player_a.mscore += 1
                match.player_b.mscore -= 1
            else:
                match.player_b.mscore += 1
                match.player_a.mscore -= 1

        table = self._players
        table = self.break_ties(table, self._tie)

        return table

    def break_ties(self, table, tie):
        #print(tie[0])
        if tie[0] == 'imscore' or tie[0] == 'isscore' or tie[0] == 'iswins':
            for p in table:
                p.imscore = 0
                p.isscore = 0
                p.iswins = 0

            combs = itertools.combinations(table, 2)
            for comb in combs:
                match = self.get_match(self._matches, comb[0], comb[1])
                res = match.random_result
                match.player_a.isscore += res[0] - res[1]
                match.player_a.iswins += res[0]
                match.player_b.isscore += res[1] - res[0]
                match.player_b.iswins += res[1]
                if res[0] > res[1]:
                    match.player_a.imscore += 1
                    match.player_b.imscore -= 1
                else:
                    match.player_b.imscore += 1
                    match.player_a.imscore -= 1

        if tie[0] == 'mscore' or tie[0] == 'sscore' or tie[0] == 'swins'\
        or tie[0] == 'imscore' or tie[0] == 'isscore' or tie[0] == 'iswins':
            key = attrgetter(tie[0])
            table = sorted(table, key=key, reverse=True)

            keyval = key(table[0])
            keyind = 0
            for i in range(1, len(table)):
                if key(table[i]) != keyval:
                    if i > keyind + 1:
                        table[keyind:i] = self.break_ties(table[keyind:i], tie)
                    keyval = key(table[i])
                    keyind = i

            if keyind < len(table) - 1 and keyind > 0:
                table[keyind:] = self.break_ties(table[keyind:], tie)
            elif keyind < len(table) - 1:
                table = self.break_ties(table, tie[1:])

        if tie[0] == 'ireplay':
            refplayers = []
            for p in table:
                p.replayed = True
                newp = playerlist.Player(copy=p)
                newp.ref = p
                refplayers.append(newp)
            smallgroup = Group(self._num, self._tie, refplayers)
            smalltable = smallgroup.simulate()

            for i in range(0,len(table)):
                table[i] = smalltable[i].ref

        return table

    def output(self, strings):
        title = str(len(self._players)) + '-player round robin'

        out = strings['header'].format(title=title)

        nm = len(self._players) - 1
        players = sorted(self._players, key=lambda p:\
                         sum(self.tally[p].finishes[0:self._threshold])*100,\
                         reverse=True)

        for p in players:
            t = self.tally[p]
            out += strings['gplayer'].format(player=p.name)
            out += strings['gpexpscore'].format(mw=(nm+t.mscore)/2,\
                    ml=(nm-t.mscore)/2, sw=t.swins, sl=t.swins-t.sscore)

            if self._threshold == 1:
                out += strings['gpprobwin'].format(prob=t.finishes[0]*100)
            else:
                out += strings['gpprobthr'].format(prob=sum(\
                        t.finishes[0:self._threshold])*100,\
                        thr=self._threshold)

            place = str(t.finishes.index(max(t.finishes)) + 1)
            if place[-1] == '1' and (place[0] != '1' or len(place) == 1):
                place += 'st'
            elif place[-1] == '2' and (place[0] != '1' or len(place) == 1):
                place += 'nd'
            elif place[-1] == '3' and (place[0] != '1' or len(place) == 1):
                place += 'rd'
            else:
                place += 'th'
            out += strings['gpmlplace'].format(place=place,\
                    prob=max(t.finishes)*100)

        out += strings['footer'].format(title=title)

        return out
