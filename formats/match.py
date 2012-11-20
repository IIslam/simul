import random

from formats.format import Format

def binomial(n, k):
    if k == 0:
        return 1
    else:
        return n/k * binomial(n-1, k-1)

class Match(Format):

    def __init__(self, num):
        Format.__init__(self, [1,1], [1,1])
        self._num = num
        self._result = (0, 0)
        self._winner_links = []
        self._loser_links = []
        self._instance_detail = None
    
    def is_fixed(self):
        return self._result[0] == self._num or self._result[1] == self._num

    def is_modified(self):
        return self._result[0] != 0 or self._result[1] != 0

    def should_use_mc(self):
        return False

    def add_winner_link(self, target, slot):
        self._winner_links.append((target, slot))
        target.add_dependency(self)

    def add_loser_link(self, target, slot):
        self._loser_links.append((target, slot))
        target.add_dependency(self)

    def can_modify(self):
        if not self.is_ready():
            return False

        for dep in self._dependencies:
            if not dep.is_fixed():
                return False

        return True

    def modify(self, num_a, num_b):
        if not self.can_modify():
            return False

        if num_a < 0 or num_b < 0 or num_a > self._num or num_b > self._num or\
           (num_a == self._num and num_b == self._num):
            return False

        if self._result[0] != num_a or self._result[1] != num_b:
            self._result = (num_a, num_b)
            self.notify()

            if self.is_fixed():
                winner = self._players[0] if num_a > num_b else self._players[1]
                loser = self._players[1] if num_a > num_b else self._players[0]
                self.broadcast_instance((0, [loser, winner], self))

        return True

    def clear(self):
        return self.modify(0, 0)

    def fill(self):
        self.notify()

    def broadcast_instance(self, instance):
        if instance[2] != self:
            raise Exception('Mismatched instance broadcast')

        for (target, slot) in self._winner_links:
            target.set_player(slot, instance[1][1])
        for (target, slot) in self._loser_links:
            target.set_player(slot, instance[1][0])

    def instances(self):
        if self.is_fixed():
            (ra, rb) = self._result
            winner = self._players[0] if ra > rb else self._players[1]
            loser = self._players[1] if ra > rb else self._players[0]
            yield (1, [loser, winner], self)
        else:
            for i in range(0,len(self._players)):
                winner = self._players[i]
                loser = self._players[1-i]
                tally = self._tally[winner]
                yield (tally[1], [loser, winner], self)

    def random_instance(self, new=False):
        if not self.is_updated():
            return None

        if not new and self._instance != None:
            return self._instance

        val = random.random()
        for instance in self.instances():
            if val >= instance[0]:
                val -= instance[0]
            else:
                self._instance = instance
                return self._instance

    def instances_detail(self):
        for outcome in self._outcomes:
            yield outcome

    def random_instance_detail(self, new=False):
        if not self.is_updated():
            return None

        if not new and self._instance_detail != None:
            return self._instance_detail

        val = random.random()
        for outcome in self.instances_detail():
            if val >= outcome[0]:
                val -= outcome[0]
            else:
                self._instance_detail = outcome
                return self._instance_detail

    def compute_mc(self):
        self.compute_exact()

    def compute_exact(self):
        start_a = self._result[0]
        start_b = self._result[1]

        if self.is_fixed():
            winner = self._players[0] if start_a > start_b else self._players[1]
            loser = self._players[1] if start_a > start_b else self._players[0]
            self._outcomes = [(1, start_a, start_b, winner, loser,\
                              max(start_a, start_b), min(start_a, start_b))]
            self._tally[winner][1] = 1
            self._tally[loser][0] = 1
            return

        pa = self._players[0].prob_of_winning(self._players[1])
        pb = 1 - pa
        num = self._num

        self._outcomes = []

        for i in range(0, num - start_b):
            base = binomial(num-start_a+i-1,i) * pa**(num-start_a) * pb**i
            self._outcomes.append((base, num, start_b+i, self._players[0],\
                                  self._players[1], num, start_b+i))
            self._tally[self._players[0]][1] += base
            self._tally[self._players[1]][0] += base

        for i in range(0, num - start_a):
            base = binomial(num-start_b+i-1,i) * pb**(num-start_b) * pa**i
            self._outcomes.append((base, start_a+i, num, self._players[1],\
                                   self._players[0], num, start_a+i))
            self._tally[self._players[1]][1] += base
            self._tally[self._players[0]][0] += base

    def detail(self, strings):
        raise NotImplementedError()

    def summary(self, strings, title=None):
        tally = self._tally

        if title == None:
            title = self._players[0].name + ' vs. ' + self._players[1].name

        out = strings['header'].format(title=title)

        ml_winner = None
        ml_winner_prob = 0
        ml_outcome = (0, 0, 0, None, None)
        i = 0
        for p in self._players:
            if tally[p][1] > ml_winner_prob:
                ml_winner_prob = tally[p][1]
                ml_winner = p

            out += strings['outcomelist'].format(player=p.name, prob=100*tally[p][1])
            for outcome in self._outcomes:
                if outcome[0] > ml_outcome[0]:
                    ml_outcome = outcome
                if outcome[3] == p:
                    out += strings['outcomei'].format(winscore=outcome[1+i],\
                            losescore=outcome[2-i], prob=100*outcome[0])

            i = 1-i

        out += strings['mlwinner'].format(player=ml_winner.name, 
                            prob=100*ml_winner_prob)

        out += strings['mloutcome'].format(pa=self._players[0].name,\
                            pb=self._players[1].name, na=ml_outcome[1],\
                            nb=ml_outcome[2], prob=100*ml_outcome[0])

        if self.image != None:
            out += strings['mimage'].format(url=self.image)

        out += strings['footer'].format(title=title)

        return out
