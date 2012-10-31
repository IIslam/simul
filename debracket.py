import match

class ScoreTally:

    def __init__(self, rounds):
        self.finishes = [0] * 2*rounds

    def compute(self):
        self.exrounds = 0
        for i in range(0,len(self.finishes)):
            self.exrounds += (len(self.finishes)-1-i) * self.finishes[i]

class DEBracket:

    def __init__(self, num, rounds, players):
        self.type = 'DEBRACKET'
        self._num = num
        self._rounds = rounds
        self._players = players
        self.setup_matches()

    def setup_matches(self):
        rounds = self._rounds

        winners = []
        losers = []
        final1 = match.Match(self._num, None, None)

        for i in range(0,rounds):
            rnd = []
            for j in range(0,2**(rounds-1-i)):
                rnd.append(match.Match(self._num, None, None))
                rnd[-1].s = 'winners-' + str(i) + '-' + str(j)
            winners.append(rnd)

        for j in range(0,len(winners[0])):
            winners[0][j].set_player(self._players[2*j], 0)
            winners[0][j].set_player(self._players[2*j+1], 1)

        for i in range(0,2*(rounds-1)):
            rnd = []
            for j in range(0,2**(rounds-2-i//2)):
                rnd.append(match.Match(self._num, None, None))
                rnd[-1].s = 'losers-' + str(i) + '-' + str(j)
            losers.append(rnd)

        for i in range(0,len(winners)):
            lbr = max(2*i-1, 0)
            flip = (i % 2 == 1)
            for j in range(0,len(winners[i])):
                if i < len(winners) - 1:
                    winners[i][j].link_winner = winners[i+1][j//2]
                    winners[i][j].link_winner_slot = j % 2
                    winners[i+1][j//2].dependences.append(winners[i][j])

                if i > 0:
                    k = j
                    if flip:
                        k = len(losers[lbr]) - 1 - k
                    winners[i][j].link_loser = losers[lbr][k]
                    winners[i][j].link_loser_slot = 0
                    losers[lbr][k].dependences.append(winners[i][j])
                else:
                    winners[i][j].link_loser = losers[0][j//2]
                    winners[i][j].link_loser_slot = j % 2
                    losers[0][j//2].dependences.append(winners[i][j])

        winners[-1][0].link_winner = final1
        winners[-1][0].link_winner_slot = 0
        final1.dependences.append(winners[-1][0])

        for i in range(0,len(losers)):
            for j in range(0,len(losers[i])):
                losers[i][j].link_loser = None
                if i % 2 == 0:
                    losers[i][j].link_winner = losers[i+1][j]
                    losers[i][j].link_winner_slot = 1
                    losers[i+1][j].dependences.append(losers[i][j])
                elif i < len(losers) - 1:
                    losers[i][j].link_winner = losers[i+1][j//2]
                    losers[i][j].link_winner_slot = j % 2
                    losers[i+1][j//2].dependences.append(losers[i][j])

        losers[-1][0].link_winner = final1
        losers[-1][0].link_winner_slot = 1
        final1.dependences.append(losers[-1][0])

        self.winners = winners
        self.losers = losers
        self.final1 = final1
        self.final2 = match.Match(self._num, None, None)
        self.final2.dependences = [final1]

    def compute(self):
        N = 10000

        tally = dict()
        for p in self._players:
            tally[p] = ScoreTally(self._rounds)
        
        for i in range(0,N):
            self.simulate(tally)

        for t in tally.values():
            t.finishes = [f/N for f in t.finishes]
            t.compute()

        self.tally = tally

    def simulate(self, tally):
        winners = self.winners
        losers = self.losers
        final1 = self.final1
        final2 = self.final2

        for i in range(0,len(winners)):
            for match in winners[i]:
                self.do_match(match, tally, -1)

        for i in range(0,len(losers)):
            for match in losers[i]:
                self.do_match(match, tally, i)

        final2.set_player_a(final1.player_a)
        final2.set_player_b(final1.player_b)

        res1 = final1.get_random_result()
        res2 = final2.get_random_result()

        if res1[0] > res1[1] or res2[0] > res2[1]:
            tally[final1.player_a].finishes[0] += 1
            tally[final1.player_b].finishes[1] += 1
        else:
            tally[final1.player_a].finishes[1] += 1
            tally[final1.player_b].finishes[0] += 1

    def do_match(self, match, tally, round):
        res = match.get_random_result()

        winner = (match.player_a if res[0] > res[1] else match.player_b)
        loser = (match.player_a if res[1] > res[0] else match.player_b)

        if match.link_winner != None:
            match.link_winner.set_player(winner, match.link_winner_slot)
        if match.link_loser != None:
            match.link_loser.set_player(loser, match.link_loser_slot)

        if round > -1:
            tally[loser].finishes[-1-round] += 1

        return winner

    def output(self, strings, title=None):
        if title == None:
            title = str(2**self._rounds) + '-man double elimination bracket'
        out = strings['header'].format(title=title)

        tally = self.tally
        players = sorted(self._players, key=lambda p: tally[p].finishes[0], reverse=True)

        out += strings['mlwinnerlist']
        for p in players[0:16]:
            out += strings['mlwinneri'].format(player=p.name,\
                                              prob=100*tally[p].finishes[0])

        players = sorted(players, key=lambda p: tally[p].exrounds, reverse=True)
        placings = [1, 1]
        for r in range(0,self._rounds-1):
            k = 2**r
            placings.append(k)
            placings.append(k)

        out += strings['exroundslist']
        for p in players:
            expl = round(tally[p].exrounds)
            if expl > 0:
                expl = sum(placings[:-expl])
            else:
                expl = sum(placings)
            expl = 'top ' + str(expl)
            out += strings['exroundsi'].format(player=p.name,\
                                               rounds=tally[p].exrounds,\
                                               expl=expl)

        out += strings['footer'].format(title=title)

        return out