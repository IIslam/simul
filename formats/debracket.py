import itertools

from formats.composite import Composite
from formats.match import Match
from formats.format import Tally as ParentTally

import progressbar

class Tally(ParentTally):

    def __init__(self, rounds, players):
        ParentTally.__init__(self, rounds)
        self.eliminators = dict()
        self.bumpers = dict()
        for p in players:
            self.eliminators[p] = 0
            self.bumpers[p] = 0

class DEBracket(Composite):

    def __init__(self, num, rounds):
        self._num = num
        self._rounds = rounds

        schema_in = [1] * 2**rounds
        schema_out = []
        r = rounds - 2
        while r >= 0:
            schema_out.append(2**r)
            schema_out.append(2**r)
            r -= 1
        schema_out += [1, 1]
        Composite.__init__(self, schema_in, schema_out)

    def setup(self):
        self._matches = dict()
        self._winners = []
        self._losers = []
        self._final = []

        prev_round = None
        L = 2**(self._rounds-1)
        for r in range(0,self._rounds):
            rnd = []
            for i in range(0,L):
                m = Match(self._num)
                rnd.append(m)

                m.add_parent(self)
                if prev_round != None:
                    prev_round[2*i].add_winner_link(m, 0)
                    prev_round[2*i+1].add_winner_link(m, 1)

            self._matches['Winner Round ' + str(r+1)] = rnd
            self._winners.append(rnd)
            prev_round = rnd

            L = L//2

        prev_round = None
        L = 2**(self._rounds-2)
        for r in range(0,2*(self._rounds-1)):
            rnd = []
            for i in range(0,L):
                m = Match(self._num)
                rnd.append(m)
                
                m.add_parent(self)
                if r == 0:
                    self._winners[0][2*i].add_loser_link(m, 0)
                    self._winners[0][2*i+1].add_loser_link(m, 1)
                elif r % 2 == 1:
                    par = i if (i % 4 == 3) else L - i - 1
                    self._winners[(r+1)//2][par].add_loser_link(m, 0)
                    prev_round[i].add_winner_link(m, 1)
                else:
                    prev_round[2*i].add_winner_link(m, 0)
                    prev_round[2*i+1].add_winner_link(m, 1)

            self._matches['Loser Round ' + str(r+1)] = rnd
            self._losers.append(rnd)
            prev_round = rnd

            if r % 2 == 1:
                L = L//2

        f1 = Match(self._num)
        f2 = Match(self._num)
        self._winners[-1][0].add_winner_link(f1, 0)
        self._winners[-1][0].add_winner_link(f2, 0)
        self._losers[-1][0].add_winner_link(f1, 1)
        self._losers[-1][0].add_winner_link(f2, 1)

        self._final.append(f1)
        self._final.append(f2)

    def get_match(self, key):
        ex = 'No such match found \'' + key + '\''

        if key == 'f1':
            return self._final[0]
        elif key == 'f2':
            return self._final[1]
        else:
            bracket = self._winners if key[:2] == 'wb' else self._losers
            key = key[2:].split('-')
            if len(key) < 2:
                raise Exception(ex)

            try:
                return bracket[int(key[0])-1][int(key[1])-1]
            except:
                raise Exception(ex)

    def should_use_mc(self):
        return self._rounds > 3

    def fill(self):
        for i in range(0,len(self._players)):
            self._winners[0][i//2].set_player(i % 2, self._players[i])

    def tally_maker(self):
        return Tally(len(self._schema_out), self._players)

    def compute_mc(self, N=50000):
        for m in self._winners[0]:
            m.compute()

        progress = progressbar.ProgressBar(N, exp='Monte Carlo')

        for i in range(0,N):
            self.compute_mc_round(0, base=1/N)

            if i % 500 == 0:
                progress.update_time(i)
                print(progress.dyn_str())

        progress.update_time(N)
        print(progress.dyn_str())
        print('')

    def compute_exact(self):
        for m in self._winners[0]:
            m.compute()

        self.compute_round(0)

    def fetch_round(self, r, master):
        if master == 0:
            mas = self._winners
        elif master == 1:
            mas = self._losers
        else:
            mas = self._final

        if master < 2:
            rnd = mas[r]
        else:
            rnd = mas

        if r > 0 or master > 0:
            for m in rnd:
                m.compute()

        return (mas, rnd)

    def compute_instances(self, instances, master, rnd, r, prob):
        if master == 0:
            for inst in instances:
                self._tally[inst[1][0]].bumpers[inst[1][1]] += prob
        elif master == 1:
            for inst in instances:
                self._tally[inst[1][0]][r] += prob
                self._tally[inst[1][0]].eliminators[inst[1][1]] += prob
        elif master == 2:
            (i1, i2) = instances
            wb_guy = rnd[0].get_player(0)
            lb_guy = rnd[0].get_player(1)
            if i1[1][1] == wb_guy or i2[1][1] == wb_guy:
                winner = wb_guy
                loser = lb_guy
                self._tally[loser].eliminators[winner] += prob
                if i1[1][1] != wb_guy:
                    self._tally[winner].bumpers[loser] += prob
            else:
                winner = lb_guy
                loser = wb_guy
                self._tally[loser].bumpers[winner] += prob
                self._tally[loser].eliminators[winner] += prob

            self._tally[winner][-1] += prob
            self._tally[loser][-2] += prob

    def compute_mc_round(self, r, master=0, base=1):
        (mas, rnd) = self.fetch_round(r, master)
        num = len(rnd)

        instances = [m.random_instance(new=True) for m in rnd]
        for inst in instances:
            inst[2].broadcast_instance(inst)

        self.compute_instances(instances, master, rnd, r, base)

        if r < len(mas) - 1 and master < 2:
            self.compute_mc_round(r+1, master, base)
        elif r == len(mas) - 1 and master < 2:
            self.compute_mc_round(0, master+1, base)

    def compute_round(self, r, master=0, base=1):
        (mas, rnd) = self.fetch_round(r, master)
        num = len(rnd)

        gens = [m.instances() for m in rnd]
        for instances in itertools.product(*gens):
            prob = base
            for inst in instances:
                prob *= inst[0]
                inst[2].broadcast_instance(inst)

            self.compute_instances(instances, master, rnd, r, prob)

            if r < len(mas) - 1 and master < 2:
                self.compute_round(r+1, master, prob)
            elif r == len(mas) - 1 and master < 2:
                self.compute_round(0, master+1, prob)

    def detail(self, strings):
        tally = self._tally

        out = strings['detailheader']

        out += strings['ptabletitle'].format(title='Detailed placement probabilities')
        out += strings['ptableheader']
        for h in range(0, len(self._schema_out)):
            if h < len(self._schema_out) - 1:
                out += strings['ptableheading'].format(heading='Top ' +\
                           str(sum(self._schema_out[h:])))
            else:
                out += strings['ptableheading'].format(heading='Win')

        for p in self._players:
            out += '\n' + strings['ptablename'].format(player=p.name)
            for i in tally[p]:
                if i > 1e-10:
                    out += strings['ptableentry'].format(prob=100*i)
                else:
                    out += strings['ptableempty']

        out += strings['ptablebetween']

        out += strings['ptabletitle'].format(title='Most likely to be eliminated by...')
        for p in self._players:
            out += '\n' + strings['ptablename'].format(player=p.name)
            elims = sorted(self._players, key=lambda a: tally[p].eliminators[a],\
                           reverse=True)
            for elim in elims[:3]:
                if tally[p].eliminators[elim] > 1e-10:
                    out += strings['ptabletextnum'].format(text=elim.name,\
                               prob=100*tally[p].eliminators[elim])

        out += strings['ptablebetween']

        out += strings['ptabletitle'].format(title='Most likely to be sent to' +\
                                             ' the losers\' bracket by...')
        for p in self._players:
            out += '\n' + strings['ptablename'].format(player=p.name)
            elims = sorted(self._players, key=lambda a: tally[p].bumpers[a],\
                           reverse=True)
            for elim in elims[:3]:
                if tally[p].bumpers[elim] > 1e-10:
                    out += strings['ptabletextnum'].format(text=elim.name,\
                               prob=100*tally[p].bumpers[elim])

        out += strings['detailfooter']

        return out

    def summary(self, strings, title=None):
        tally = self._tally

        if title == None:
            title = str(2**self._rounds) + '-man double elimination bracket'
        out = strings['header'].format(title=title)

        players = sorted(self._players, key=lambda a: tally[a][-1],\
                         reverse=True)

        out += strings['mlwinnerlist']
        for p in players[0:16]:
            if tally[p][-1] > 1e-10:
                out += strings['mlwinneri'].format(player=p.name,\
                                                   prob=100*tally[p][-1])

        def exp_rounds(k):
            ret = 0
            for i in range(0,len(k)):
                ret += i*k[i]
            return ret

        players = sorted(self._players, key=lambda a: exp_rounds(tally[a]), 
                         reverse=True)

        out += strings['exroundslist']
        for p in players:
            exp = exp_rounds(tally[p])
            rounded = round(exp)
            expl = 'top ' + str(sum(self._schema_out[rounded:]))

            out += strings['exroundsi'].format(player=p.name, rounds=exp,\
                                               expl=expl)

        out += strings['footer']

        return out
