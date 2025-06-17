import math
import random
import collections

class Strategy:
    def predict(self, history):
        pass

    def update(self, my_move, opponent_move):
        pass


# --- Strategy Implementations ---
class FrequencyCounter(Strategy):
    def __init__(self):
        self.counts = {"R": 0, "P": 0, "S": 0}

    def predict(self, history):
        return max(self.counts, key=self.counts.get)

    def update(self, my_move, opponent_move):
        self.counts[opponent_move] += 1


class FirstOrderMarkov(Strategy):
    def __init__(self):
        self.transitions = {"R": {"R": 1, "P": 1, "S": 1},
                            "P": {"R": 1, "P": 1, "S": 1},
                            "S": {"R": 1, "P": 1, "S": 1}}
        self.last = None

    def predict(self, history):
        if not self.last:
            return random.choice(["R", "P", "S"])
        next_probs = self.transitions[self.last]
        return max(next_probs, key=next_probs.get)

    def update(self, my_move, opponent_move):
        if self.last:
            self.transitions[self.last][opponent_move] += 1
        self.last = opponent_move


class MirrorStrategy(Strategy):
    def predict(self, history):
        if not history:
            return random.choice(["R", "P", "S"])
        return history[-1][1]  # Opponent's last move

    def update(self, my_move, opponent_move):
        pass


class FuzzyVotingStrategy(Strategy):
    def __init__(self, strategies):
        self.strategies = strategies

    def predict(self, history):
        vote = {"R": 0, "P": 0, "S": 0}
        for s in self.strategies:
            prediction = s.predict(history)
            vote[prediction] += 1
        return max(vote, key=vote.get)

    def update(self, my_move, opponent_move):
        for s in self.strategies:
            s.update(my_move, opponent_move)


# --- Contextual Bandit Controller ---
class BanditController:
    def __init__(self, strategies):
        self.strategies = strategies
        self.context_memory = {}

    def _context_key(self, history):
        if len(history) < 3:
            return (None, None, None)
        return tuple(history[-3:])

    def select_strategy(self, history):
        context = self._context_key(history)
        if context not in self.context_memory:
            self.context_memory[context] = {
                i: [0.0, 1] for i in range(len(self.strategies))
            }
        total = sum(c for _, c in self.context_memory[context].values())
        ucb_scores = [
            (self.context_memory[context][i][0] / self.context_memory[context][i][1]) +
            (2 * (math.log(total) / self.context_memory[context][i][1]) ** 0.5)
            for i in range(len(self.strategies))
        ]
        return ucb_scores.index(max(ucb_scores))

    def update(self, history, index, reward):
        context = self._context_key(history)
        if context not in self.context_memory:
            self.context_memory[context] = {
                i: [0.0, 1] for i in range(len(self.strategies))
            }
        self.context_memory[context][index][0] += reward
        self.context_memory[context][index][1] += 1


# --- Utility Functions ---
def counter_move(move):
    # Add bluffing chance
    if random.random() < 0.05:
        return random.choice(["R", "P", "S"])
    return {"R": "P", "P": "S", "S": "R"}[move]

def get_reward(my_move, opponent_move):
    if my_move == opponent_move:
        return 0
    if (my_move, opponent_move) in [("R", "S"), ("P", "R"), ("S", "P")]:
        return 1
    return -1

def get_opponent_move():
    while True:
        choice = input("Your move: ").upper()
        if choice in 'RPS' and choice != '':
            return choice
        if choice == 'E':
            exit()
        print('Please use R, P, or S. Use E to end the game')
    

def entropy(moves):
    counts = collections.Counter(moves)
    total = sum(counts.values())
    if total > 0:
        results = []
        for count in counts.values():
            ratio = count / total
            result = ratio * math.log2(ratio)
            results.append(result)

        return -sum(results)
    else:
        return 0


# --- Main Loop ---
def play_rps(rounds=100):
    history = []
    raw_opponent_moves = []
    base_strategies = [FrequencyCounter(), FirstOrderMarkov(), MirrorStrategy()]
    fuzzy = FuzzyVotingStrategy(base_strategies)
    strategies = base_strategies.append(fuzzy)
    bandit = BanditController(strategies)

    entropy_threshold = 1.5
    entropy_window = 10
    entropy_stable_rounds = 0

    plays = 0
    entropy_counter = 0
    ai_wins = 0
    player_wins = 0
    while True:
        plays += 1
        entropy_counter += 1
        strat_idx = bandit.select_strategy(history)
        strategy = strategies[strat_idx]

        opponent_pred = strategy.predict(history)
        my_move = counter_move(opponent_pred)

        opponent_move = get_opponent_move()
        raw_opponent_moves.append(opponent_move)

        # Meta-switching (detect strategy change)
        if entropy_counter >= entropy_window:
            recent_entropy = entropy(raw_opponent_moves[-entropy_window:])
            if recent_entropy > entropy_threshold:
                entropy_stable_rounds += 1
            else:
                entropy_stable_rounds = 0

            if entropy_stable_rounds >= 3:
                entropy_counter %= entropy_window
                bandit = BanditController(strategies)
                entropy_stable_rounds = 0

        reward = get_reward(my_move, opponent_move)
        bandit.update(history, strat_idx, reward)

        for strat in strategies:
            strat.update(my_move, opponent_move)

        history.append((my_move, opponent_move))
        player_won = reward == 0
        if player_won:
            player_wins += 1
        else:
            ai_wins += 1
        ratio = ai_wins / plays
        message = 'You win!' if player_won else 'AI wins!'
        print(f"You: {opponent_move}, AI: {my_move}, {message} Ratio: {ratio*100}%")


if __name__ == "__main__":
    play_rps()
