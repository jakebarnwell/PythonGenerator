import sys
import math
import time
import random
from collections import deque
from mylogger import getLogger
import inspect

UNSEEN = 1
WATER = 2
LAND = 4
FOOD = 8
MY_HILL = 16
ENEMY_HILL = 32
DEAD_ANT = 64
MY_ANT = 128
ENEMY_ANT = 256

#UNPASSABLE = (WATER | FOOD | MY_ANT)
UNPASSABLE = (WATER | FOOD)
ENEMY_UNPASSABLE = (WATER | FOOD | ENEMY_ANT)

REWARDS = {
        UNSEEN : 0,
        WATER : -1,
        LAND : 0,
        FOOD : 1000,
        MY_HILL : -2,
        ENEMY_HILL : 10000
        }

def abs(val):
    if val < 0:
        return (-val)
    return val

class docache(object):
    def __init__(self, obj):
        self.__cache = {}
        if inspect.isfunction(obj):
            self.f = obj
            self.callable = self.__decorated_function__
        else:
            self.obj = obj
            self.callable = self.__decorated_method__

    def __decorated_function__(self, *args):
        if self.__cache.has_key(args):
            return self.__cache[args]
        ret = self.f(self.obj, *args)
        self.__cache[args] = ret
        return ret

    def __decorated_method__(self, f):
        def wrapped_f(*args):
            if self.__cache.has_key(args):
                return self.__cache[args]
            ret = f(*args)
            self.__cache[args] = ret
            return ret

        return wrapped_f

    def __call__(self, *args):
        return self.callable(*args)

class Ant(object):
    def __init__(self, loc):
        self.id = loc
        self.prev_dir = None
        self.visited_cnt = {}
        self.visited_milestones = {}
        self.visible_milestones = []
        self.curr_milestone = None
        self.last_milestone = None

    def __str__(self):
        return "Ant (%d), visible_milestones: %s, curr_milestone: (%s), last_milestone: (%s), visited_milestones: (%s)" % (
                self.id, self.visible_milestones, str(self.curr_milestone), str(self.last_milestone), str(self.visited_milestones))
                
class Engine(object):
    Self = None

    def __init__(self):
        self.cols = 0
        self.rows = 0
        self.turntime = 0
        self.loadtime = 0
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawmradius2 = 0
        self.turns = 0
        self.map_data = []
        self.my_ants = {}
        self.enemy_ant_list = []
        self.my_hills = []
        self.enemy_hills = []
        self.food = {}
        self.dead_ants = {}
        self.orders = {}
        self.turn = 0
        Self = self

    def do_setup(self):
        self.size = self.rows * self.cols
        self.viewradius = int(math.sqrt(self.viewradius2))
        self.scan_radius = 4*self.viewradius2
        self.attackradius = math.sqrt(self.attackradius2)
        self.depthwise_radius2 = [self.attackradius2 + int(2*i*self.attackradius + i**2) + 1 for i in range(1, 12, 2)]
        self.attackradius = int(self.attackradius)
        self.battleradius2 = self.attackradius2 + 4*self.attackradius + 5
        self.available_ants = {}
        self.spiral_dirs = (('e', 'n', 'w', 's'), ('w', 'n', 's', 'e'))
        self.food_rewards = {}
        self.hill_rewards = {}
        self.enemy_ant_rewards = {}
        self.old_food = {}
        self.attackradius_proj = int(math.sqrt(self.attackradius2/2.0))
        self.directions = list(self.spiral_dirs[0])
        self.visible = {}
        self.visited_cnt = [0 for i in range(self.size)]
        self.exploration_points = [0 for i in range(self.size)]
        self.new_food = {}
        self.my_scent = {}
        self.my_hill_distance = {}
        self.battle_clusters = {}
        self.my_rivals = {}
        self.my_warriors = {}
        self.defenders = {}
        self.watchmen = {}
        self.enemy_targets = {}
        self.kill_orders = {}
        self.distance_sq_cache = {}
        self.distance_sq_xdiff_cache = {}
        self.distance_sq_ydiff_cache = {}
        self.milestones = {}
        self.unvisited_milestones = {}
        self.milestone_rewards = {}
        self.explore_targets = []
        self.nearest_milestone = {}
        self.generate_milestones()
        self.movers = {}
        self.seen_milestones = {}

    def generate_milestones(self):
        # Divide the map into smaller (manageable) targets. 
        # A*/BFS can be applied on the targets for better exploration
        viewradius_half = self.viewradius/2
#viewradius_half = self.viewradius
        viewradius_quarter = viewradius_half/2
        for i in range(0, self.rows/viewradius_half - 1):
            midx_partial_sum = self.cols * (i * viewradius_half + viewradius_quarter)
            for r in range(i * viewradius_half, (i+1)*viewradius_half):
                partial_sum = self.cols * r
                for j in range(0, self.cols/viewradius_half - 1):
                    mid = midx_partial_sum + j * viewradius_half + viewradius_quarter
                    self.milestones[mid] = 1
                    for c in range(j * viewradius_half, (j+1) * viewradius_half):
                        loc = partial_sum + c
                        self.nearest_milestone[loc] = mid
        self.unvisited_milestones = self.milestones.copy()
        self.milestone_rewards = dict([(i, {}) for i in self.milestones.keys()])
        getLogger().debug("Milestones: " + str([(i/self.cols, i%self.cols) for i in sorted(self.milestones.keys())]))

    def cleanup(self):
        for loc in self.dead_ants:
            self.map_data[loc] = LAND
        for loc in self.enemy_ant_list:
            self.map_data[loc] = LAND
        del self.enemy_ant_list[:]
        for loc in self.my_ants:
            self.map_data[loc] = LAND
        self.available_ants.clear()
        self.new_food.clear()
        self.my_rivals.clear()
        self.my_warriors.clear()
        self.defenders.clear()
        self.watchmen.clear()
        self.movers.clear()
        del self.explore_targets[:]

    def distance_sq(self, src, dest):
        key = (src, dest)
        if not self.distance_sq_cache.has_key(key):
            x = abs((dest % self.cols) - (src % self.cols))
            y = abs((dest / self.cols) - (src / self.cols))
        
            if not self.distance_sq_xdiff_cache.has_key(x):
                if x > self.cols/2:
                    x = self.cols - x
                X = x *x
                self.distance_sq_xdiff_cache[x] = X
            else:
                X = self.distance_sq_xdiff_cache[x]

            if not self.distance_sq_ydiff_cache.has_key(y):
                if y > self.rows/2:
                    y = self.rows - y
                Y = y * y
                self.distance_sq_ydiff_cache[y] = Y
            else:
                Y = self.distance_sq_ydiff_cache[y]
            self.distance_sq_cache[key] = X + Y
        return self.distance_sq_cache[key]

    def distant_location(self, loc, row_offset, col_offset):
        row, col = loc / self.cols, loc % self.cols
        new_row = (row + row_offset) % self.rows
        new_col = (col + col_offset) % self.cols
        return new_row * self.cols + new_col

    @docache(Self)
    def new_loc(self, src, dir):
        if dir == 'n':
            dest = (src - self.cols) % self.size
        elif dir == 's':
            dest = (src + self.cols) % self.size
        elif dir == 'w':
            if src % self.cols:
                dest = src - 1
            else:
                dest = src + self.cols - 1
        elif dir == 'e':
            dest = src + 1
            if not dest % self.cols:
                dest = dest - self.cols
        else:
            dest = src
        return dest

    def try_move(self, src, sorted_dirs):
        for i, d in enumerate(sorted_dirs):
            if self.do_move(src, d):
                return True
            new_loc = self.new_loc(src, d)
            if self.map_data[new_loc] == MY_ANT:
                self.deferred_moves[new_loc] = sorted_dirs[i:]
                return True
        return False

    def do_move(self, src, dir):
        dest = self.new_loc(src, dir)
        if self.orders.has_key(dest):
            return False
        if src == dest:
            self.orders[dest] = src
            self.movers[src] = dest
            self.visited_cnt[dest] += 1
            self.my_ants[src].visited_cnt[dest] = 1 + self.my_ants[src].visited_cnt.get(dest, 0)
            return True
        if (self.map_data[dest] == WATER) or (self.map_data[dest] == FOOD):
            return False
        if self.map_data[dest] == MY_ANT:
            if self.movers.has_key(dest):
                if self.movers[dest] == dest:
                    return False
            else:
                return False

        self.orders[dest] = src
        self.movers[src] = dest
        output_str = 'o %s %s %s\n' % (src / self.cols, src % self.cols, dir)
        sys.stdout.write(output_str)
        sys.stdout.flush()
        getLogger().debug(output_str)
        for k, v in self.my_hill_distance.iteritems():
            v[dest] = self.compute_distance(dest, v)
        for k, v in self.hill_rewards.iteritems():
            v[dest] = self.compute_qvalue(dest, v)
            for i in self.directions:
                next_loc = self.new_loc(src, i)
                v[next_loc] = self.compute_qvalue(next_loc, v)
                for j in self.directions:
                    next_next_loc = self.new_loc(next_loc, j)
                    v[next_next_loc] = self.compute_qvalue(next_next_loc, v)
        self.visited_cnt[dest] += 1
        self.my_ants[src].visited_cnt[dest] = 1 + self.my_ants[src].visited_cnt.get(dest, 0)
        self.my_ants[src].prev_dir = dir
        if self.milestones.has_key(dest):
            self.my_ants[src].visited_milestones[dest] = True
            self.my_ants[src].last_milestone = dest
        return True

    def do_move_loc(self, src, dest):
        dir = self.aim(src, dest)[0]
        return self.do_move(src, dir)

    def aim(self, src, dest):
        src_r, src_c = src / self.cols, src % self.cols
        dest_r, dest_c = dest / self.cols, dest % self.cols

        directions = set()
        # Compute North/South direction
        diff = dest_r - src_r
        if abs(diff) > self.rows/2:
            if diff > 0:
                directions.add('n')
            elif diff < 0:
                directions.add('s')
        elif diff > 0:
            directions.add('s')
        elif diff < 0:
            directions.add('n')

        # Compute East/West direction
        diff = dest_c - src_c
        if abs(diff) > self.cols/2:
            if diff > 0:
                directions.add('w')
            elif diff < 0:
                directions.add('e')
        elif diff > 0:
            directions.add('e')
        elif diff < 0:
            directions.add('w')

        return directions

    def repel(self, src, dest):
        opposites = {
            'n' : 's',
            'e' : 'w',
            'w' : 'e',
            's' : 'n'
        }

        return [opposites[i] for i in self.aim(src, dest)]

    def compute_qvalue(self, dest, rewards):
        directions = self.directions
        computed = max([rewards.get(self.new_loc(dest, i), 0) for i in directions]) - 1
        old = rewards.get(dest, 0)
        return max(old, computed)

    def compute_distance(self, dest, distance_matrix):
        min_dist = 99999
        if self.map_data[dest] == WATER:
            return min_dist
        elif self.map_data[dest] == UNSEEN:
            return min_dist
        for d in self.directions:
            new_loc = self.new_loc(dest, d)
            if self.map_data[new_loc] == WATER:
                continue
            if self.map_data[new_loc] == UNSEEN:
                continue
            dist = distance_matrix.get(new_loc, 99999)
            if dist < min_dist:
                min_dist = dist
        return min(distance_matrix.get(dest, 99999), min_dist + 1)

    def loc_str(self, loc):
        return "(%d, %d)" % (loc/self.cols, loc%self.cols)

    def fill_MDP_values_BFS(self, loc, radius2, MDP_rewards, heuristics, preempt=False, base=40000):
        wip = deque([loc])
        if heuristics:
            MDP_rewards[loc] = max(MDP_rewards.get(loc, 0), heuristics.get(self.map_data[loc], 0))
        else:
            MDP_rewards[loc] = max(MDP_rewards.get(loc, 0), base)
        seen = {loc : True}
        #getLogger().debug("Filling MDP values for %s" % self.loc_str(loc))
        while wip and (radius2 > 0):
            dest = wip.popleft()
            if preempt and (self.map_data[dest] == MY_ANT):
                break
            #getLogger().debug("Removed %s from WIP queue" % self.loc_str(dest))
            for i in self.directions:
                next_loc = self.new_loc(dest, i)
                if seen.has_key(next_loc):
                    continue
                obj = self.map_data[next_loc]
                if (obj == WATER) or (obj == UNSEEN):
                    MDP_rewards[next_loc] = -1
                    seen[next_loc] = True
                    #MDP_rewards[dest] = 0
                    continue
                wip.append(next_loc)
                #getLogger().debug("Added %s to QIP queue" % self.loc_str(next_loc))
                seen[next_loc] = True
            MDP_rewards[dest] = self.compute_qvalue(dest, MDP_rewards)
            radius2 -= 1
            #getLogger().debug(MDP_rewards[dest])
            #getLogger().debug([self.loc_str(i) for i in wip])




    def fill_MDP_values(self, loc, radius2, dir_index, MDP_rewards, heuristics):
        for directions in self.spiral_dirs:
            repeat_cnt_preset = 1
            dir_change_cnt = 0
            repeat_cnt = repeat_cnt_preset
        
            dest = loc
            obj = self.map_data[dest]
            MDP_rewards[dest] = max(MDP_rewards.get(dest, 0), heuristics.get(obj, 0))
            for i in range(radius2):
                if not repeat_cnt:
                    dir_index = (dir_index + 1) % 4
                    dir_change_cnt += 1
                    if not dir_change_cnt % 2:
                        repeat_cnt_preset += 1
                    repeat_cnt = repeat_cnt_preset
                repeat_cnt -= 1
                dest = self.new_loc(dest, directions[dir_index])
                obj = self.map_data[dest]
                if (obj == WATER) or (obj == UNSEEN):
                    #MDP_rewards[dest] = -1
                    MDP_rewards[dest] = 0
                else:
                    MDP_rewards[dest] = self.compute_qvalue(dest, MDP_rewards)

    def get_circular_area(self, loc, radius2):
        radius = int(math.sqrt(radius2))
        radius_proj = math.sqrt(radius2/2.0)
        if radius_proj == int(radius_proj):
            radius_proj = int(radius_proj)
        else:
            radius_proj = int(radius_proj) + 1
        squares = set()

        for x in range(-radius_proj, radius_proj + 1):
            for y in range(-radius_proj, radius_proj + 1):
                squares.add(self.distant_location(loc, x, y))

        for x in range(radius_proj, radius + 1):
            x2 = x * x
            for y in range(0, radius_proj + 1):
                if x2 + y * y <= radius2:
                    squares.add(self.distant_location(loc, x, y))
                    squares.add(self.distant_location(loc, x, -y))
                    squares.add(self.distant_location(loc, -x, y))
                    squares.add(self.distant_location(loc, -x, -y))
                    squares.add(self.distant_location(loc, y, x))
                    squares.add(self.distant_location(loc, y, -x))
                    squares.add(self.distant_location(loc, -y, x))
                    squares.add(self.distant_location(loc, -y, -x))
        return squares

    def get_battle_area(self, radius2):
        area = {}
        for enemy in self.enemy_ant_list:
            squares = self.get_circular_area(enemy, radius2)
            for s in squares:
                if area.has_key(s):
                    area[s].append(enemy)
                else:
                    area[s] = [enemy]
        return area

    def explore_milestones(self, loc):
        ant = self.my_ants[loc]

        def _chase_milestone_(milestone):
            getLogger().debug("Chasing milestone: %s" % self.loc_str(milestone))
            ant.curr_milestone = milestone
            rewards = {'n' : 0, 'w' : 0, 's' : 0, 'e' : 0}
            directions = rewards.keys()
            for i in directions:
                new_loc = self.new_loc(loc, i)
                reward = self.milestone_rewards[milestone].get(new_loc, 0)
                for r in self.hill_rewards.values():
                    if r.has_key(new_loc):
                        reward += r[new_loc]
                        break
                rewards[i] = reward

            directions.sort(key=rewards.get, reverse=True)
            getLogger().debug("Explore rewards: %s" % str(rewards))
            if rewards[directions[0]] == rewards[directions[-1]]:
                return False
            self.try_move(loc, directions)
            return True

        def _chase_random_milestone_():
            milestones = [i for i in ant.visible_milestones if ((i != ant.last_milestone) and (self.milestones[i]))]
#milestones = [i for i in ant.visible_milestones if (self.milestones[i])]
            random.shuffle(milestones)
            for milestone in milestones:
                if _chase_milestone_(milestone):
                    return True
            return False
            

        getLogger().debug("Explore details for ant %s" % self.loc_str(loc))
        getLogger().debug(ant)
        for d in self.directions:
            new_loc = self.new_loc(loc, d)
            if self.milestones.has_key(new_loc):
                ant.visited_milestones[new_loc] = True
            if new_loc == ant.curr_milestone:
                ant.last_milestone = new_loc
                ant.curr_milestone = None
        if not ant.curr_milestone:
            milestones = [i for i in ant.visible_milestones if ((not ant.visited_milestones.has_key(i)) and self.milestones[i])]
#if not milestones:
# milestones = [i for i in ant.visible_milestones if self.milestones[i]]
            if not milestones:
#return self.explore(loc)
                return _chase_random_milestone_()
            milestones.sort(key=lambda x: self.distance_sq(x, loc), reverse=True)
            ant.curr_milestone = milestones[-1]
            del milestones[-1:]
        elif ant.curr_milestone == loc:
            # Target achieved! Take up a new target.
            getLogger().debug("Target achieved: Need to change milestone")
            ant.visited_milestones[loc] = True
            milestones = [i for i in ant.visible_milestones if ((i != loc) and (not ant.visited_milestones.has_key(i)) and self.milestones[i])]
            ant.last_milestone = loc
#if not milestones:
#milestones = [i for i in ant.visible_milestones if ((i != loc) and self.milestones[i])]
            if not milestones:
#return self.explore(loc)
                return _chase_random_milestone_()
            milestones.sort(key=lambda x: self.distance_sq(x, loc), reverse=True)
            ant.curr_milestone = milestones[-1]
            del milestones[-1:]
        else:
            milestones = [i for i in ant.visible_milestones if ((i != loc) and (i != ant.curr_milestone) and (not ant.visited_milestones.has_key(i)) and self.milestones[i])]
            milestones.sort(key=lambda x: self.distance_sq(x, loc), reverse=True)

        if not _chase_milestone_(ant.curr_milestone):
            if not milestones:
                if _chase_random_milestone_():
                    return True
                
            for milestone in milestones:
                if _chase_milestone_(milestone):
                    return True
        return False
#return self.explore(loc)
        return self.random_explore(loc)


    def explore(self, loc):
        opposites = {
            'n' : 's',
            'w' : 'e',
            's' : 'n',
            'e' : 'w'
        }
        def _evaluate_pos_(loc, ant):
            score = 0
            old_hill_dist = {}
            for k, v in self.my_hill_distance.iteritems():
                dist = v.get(loc, self.compute_distance(loc, v))
                if dist > 50000:
                    continue
                score += 5*dist
            for k, v in self.hill_rewards.iteritems():
                v[loc] = self.compute_qvalue(loc, v)
                score += v[loc]
            if not self.visited_cnt[loc]:
                score += 1
            if self.my_ants[ant].visited_cnt.get(loc, 0) > 0:
                score -= 1000*self.my_ants[ant].visited_cnt[loc]
            for d in self.directions:
                if self.map_data[self.new_loc(loc, d)] == MY_ANT:
                    score -= 1
            return score
               
        def _evaluate_dirs_(curr_loc, prev_dir, evaluated):
            scores = {}
            for d in self.directions:
                next_loc = self.new_loc(curr_loc, d)
                if evaluated.has_key(next_loc) or (self.map_data[next_loc] == WATER):
                    continue
                if self.orders.has_key(next_loc):
                    continue
                scores[d] = _evaluate_pos_(next_loc, loc)
                if d == prev_dir:
                    # Try to continue in the same direction
                    scores[d] += 10
                evaluated[next_loc] = True
                child_scores = [self.exploration_points[self.new_loc(next_loc, i)] for i in self.directions if opposites[i] != d]
                scores[d] = 13*scores[d] + max(child_scores or [0])
                self.exploration_points[next_loc] = (2*self.exploration_points[next_loc] + scores[d]) / 16
            return scores

        prev_dir = self.my_ants[loc].prev_dir
        scores = _evaluate_dirs_(loc, prev_dir, {})
        #getLogger().debug("EXPLORE: ant (%d, %d): %s" % (loc/self.cols, loc%self.cols, scores))

        sorted_dirs = sorted(scores.keys(), key=scores.get, reverse=True)
        if len(sorted_dirs) > 1 and (scores[sorted_dirs[0]] == scores[sorted_dirs[-1]]):
            random.shuffle(sorted_dirs)
        return self.try_move(loc, sorted_dirs)
        for i in sorted_dirs:
            if self.do_move(loc, i):
                return True
        return False

    def gather(self, loc):
        directions = self.directions
        best_val = self.food_rewards.get(loc, self.turn)
        best_dir = None
        #getLogger().debug("Scanning best direction for ant (%d, %d)" % (loc/self.cols, loc%self.cols))
        rewards = {'n' : 0, 'w' : 0, 's' : 0, 'e' : 0}
        for i in directions:
            new_loc = self.new_loc(loc, i)
            reward = self.food_rewards.get(new_loc, 0)
            for r in self.hill_rewards.values():
                if r.has_key(new_loc):
                    reward += r[new_loc]
                    break
            rewards[i] = reward

        #getLogger().debug("REWARDS: %s" % str(rewards))
        directions.sort(key=rewards.get, reverse=True)
        if rewards[directions[0]] == rewards[directions[-1]]:
            return False
        for best_dir in directions:
            #d = self.gather_probabilities[best_dir][random.randint(0, 99)]
            d = best_dir
            if self.do_move(loc, d):
                self.available_ants.pop(loc)
                break
        return True

    def update_MDP(self):
        self.food_rewards.clear()
        for hill in self.hill_rewards.keys():
            if self.map_data[hill] != ENEMY_HILL:
                self.hill_rewards.pop(hill)
        for loc in self.enemy_hills:
            self.fill_MDP_values_BFS(loc, 1600, self.hill_rewards[loc], REWARDS)
        for loc in self.food:
            self.fill_MDP_values_BFS(loc, 4*self.viewradius2, self.food_rewards, REWARDS, preempt=True)
#for loc in self.explore_targets:
#self.fill_MDP_values_BFS(loc, 4*self.viewradius2, self.milestone_rewards[loc], {})

    def update_visible(self):
        def _degrees_of_freedom_(loc):
            entry_points = []
            for d in self.directions:
                next_loc = self.new_loc(i, d)
                if not self.map_data[next_loc] == WATER:
                    entry_points.append(next_loc)
            return entry_points

        self.visible.clear()
        for loc in self.my_ants:
            ant = self.my_ants[loc]
            del ant.visible_milestones[:]
            squares = self.get_circular_area(loc, self.viewradius2)
            for i in squares:
                if self.map_data[i] == UNSEEN:
                    self.map_data[i] = LAND
                if self.milestones.has_key(i):
                    self.seen_milestones[i] = 1
                self.visible[i] = 1
                if self.unvisited_milestones.has_key(i):
                    if self.map_data[i] == WATER:
                        self.milestones[i] = False
                        self.unvisited_milestones.pop(i)
                    else:
                        entry_points = _degrees_of_freedom_(i)
#if len(entry_points) > 1:
                        if len(entry_points) > 0:
                            ant.visible_milestones.append(i)
                        else:
                            for entry_point in entry_points:
                                if len(_degrees_of_freedom_(entry_point)) > 1:
                                    ant.visible_milestones.append(entry_point)
                                    self.unvisited_milestones[entry_point] = True
                                    ant.curr_milestone = entry_point
                                    self.milestones[entry_point] = True
                                    break
                            self.milestones[i] = False
                            self.unvisited_milestones.pop(i)
                            if ant.curr_milestone == i:
                                ant.curr_milestone = None
            getLogger().debug("Ant %s, visible_milestones: %s" % (self.loc_str(loc), [self.loc_str(i) for i in ant.visible_milestones]))

    def update_battle_clusters(self):
        area = self.get_battle_area(self.battleradius2)
        for my_ant in self.available_ants.keys():
            if area.has_key(my_ant):
                self.my_warriors[my_ant] = [(i, self.distance_sq(my_ant, i)) for i in area[my_ant]]
                # Sort enemies, pitted against my ant according to increasing distance
                #getLogger().debug("WARRIORS: %s, my_ant: %d" % (str(self.my_warriors), my_ant))
                self.my_warriors[my_ant].sort(key=lambda x: x[1])
                for enemy in area[my_ant]:
                    if self.my_rivals.has_key(enemy):
                        self.my_rivals[enemy].append(my_ant)
                    else:
                        self.my_rivals[enemy] = [my_ant]

        # Sort my ants, pitted against each enemy according to increasing distance
        #for enemy in self.my_rivals:
            #getLogger().debug("ENEMY: %d, rivals: %s" % (enemy, self.my_rivals))
            #self.my_rivals[enemy].sort(key=lambda x: self.my_warriors[x][enemy])

    def escape_evaluate(self, warrior, old_loc, direction, battleradius2):
        # Indicates how good the given location is, for escape
        loc = self.new_loc(old_loc, direction)
        if self.orders.has_key(loc):
            return 0
        score = 0
        for rival, dt in self.my_warriors[warrior]:
            new_dt = self.distance_sq(rival, loc)
            if new_dt <= battleradius2:
                return -99999
            score += new_dt
        return score

    def greedy_evaluate(self, warrior, old_loc, direction, battleradius2):
        # Indicates if a one to one stalemate is possible
        loc = self.new_loc(old_loc, direction)
        if self.orders.has_key(loc):
            return 0
        score = 0
        rival_cnt = 0
        for rival, dt in self.my_warriors[warrior]:
            new_dt = self.distance_sq(rival, loc)
            if new_dt <= battleradius2:
                rival_cnt += 1
                if rival_cnt > 1:
                    return -99999
                score += 1000
            else:
                score -= 100
        return score


    def heuristic_evaluate(self, warrior, old_loc, direction, battleradius2):
        loc = self.new_loc(old_loc, direction)
        if self.orders.has_key(loc):
            return -99999
        if (loc != old_loc) and (self.map_data[loc] & UNPASSABLE):
            return -99999

        #getLogger().debug("WARRIOR: (%d, %d), old_loc: (%d, %d), new_loc: (%d, %d), direction: %s" % (warrior/self.cols, warrior%self.cols, old_loc/self.cols, old_loc%self.cols, loc/self.cols, loc%self.cols, direction))
        #getLogger().debug("Battleradius squared: %d" % battleradius2)
        #rivals = sorted([i for i in self.my_warriors[warrior] if i[1] < battleradius2], key=lambda x: x[1])
        rivals = sorted([i for i in self.my_warriors[warrior]], key=lambda x: x[1])
        rival_cnt = 0
        closest_rival = None
        closest_rival_dir = None
        closest_rival_new_loc = None
        score = 0
        closest_dt = 99999
        closest_enemy = None
        for rival, dt in rivals:
            #getLogger().debug("RIVAL: (%d, %d), distance: %d" % (rival/self.cols, rival%self.cols, dt))
            for d in ('n', 's', 'w', 'e', 'o'):
                #getLogger().debug("Evaluating rival movement in %s direction..." % d)
                new_rival_loc = self.new_loc(rival, d)
                new_enemy_dt = self.distance_sq(loc, new_rival_loc)
                if new_enemy_dt < closest_dt:
                    closest_dt = new_enemy_dt
                    closest_enemy = rival
                    closest_enemy_new_loc = new_rival_loc
                #getLogger().debug("New distance squared: %d" % (new_enemy_dt))
                if self.map_data[new_rival_loc] & ENEMY_UNPASSABLE:
                    continue
                if new_enemy_dt <= self.attackradius2:
                    rival_cnt += 1
                    closest_rival = rival
                    closest_rival_dir = d
                    closest_rival_new_loc = new_rival_loc
                    break
        if rival_cnt > 1:
            # More than one enemies attacking me, meaning a suicide
            #getLogger().debug("Trying to avoid SUICIDE movement")
            return -99999

        if closest_rival:
            #getLogger().debug("DUEL with (%d, %d) possible" % (closest_rival/self.cols, closest_rival%self.cols))
            # Now see if the closest_rival can be attacked together with allies
            allies = [i for i in self.my_rivals[closest_rival] if i != warrior]
            for ally in allies:
                #getLogger().debug("Checking if (%d, %d) can be of help..." % (ally/self.cols, ally%self.cols))
                #for enemy, ally_dt in self.my_warriors[ally]:
                #    if enemy == closest_rival:
                #        break
                for d in ('n', 'w', 's', 'e', 'o'):
                    new_ally_loc = self.new_loc(ally, d)
                    if new_ally_loc == loc:
                        continue
                    if self.distance_sq(new_ally_loc, closest_rival_new_loc) > self.attackradius2:
                        continue
                    if self.orders.has_key(new_ally_loc):
                        return 99999
                    if self.map_data[new_ally_loc] & UNPASSABLE:
                        continue
                    # The enemy is going to be most likely killed without any losses to self
                    #getLogger().debug("Moving of ally towards %s seems advantageous" % d)
                    return 99999

            # Lone Wolf!
            # Now need to take a decision on when to consider 
            # battling, if there is a one to one battle
            #getLogger().debug("LONE WOLF")
            if self.defenders.has_key(loc):
                # When defending, always move towards the enemy.
                return 10
            return -10
            score = self.food_rewards.get(loc, 0)
            for hill in self.enemy_hills:
                if self.hill_rewards[hill].get(loc, 0) > (REWARDS[ENEMY_HILL] - self.viewradius):
                    score += self.hill_rewards[hill].get(loc, 0)
            if score <= 0:
                return -10
            return score
                
        #getLogger().debug("Outside enemy attack range!!!")
        # When outside the range of the enemy, use the following heuristics
        allies = [i for i in self.my_rivals[closest_enemy] if i != warrior]
        my_quad = self.aim(closest_enemy_new_loc, loc)
        for ally in allies:
            score += 1
            ally_quad = self.aim(closest_enemy_new_loc, ally)
            if ally_quad.issubset(my_quad):
                score += 10
            elif my_quad.issubset(ally_quad):
                score += 10
            elif ally_quad.intersection(my_quad):
                score += 2
            score += 100 - self.distance_sq(closest_enemy_new_loc, ally)
        old_dt = self.distance_sq(old_loc, closest_enemy)
        if closest_dt > old_dt:
            score -= 100
        else:
            # Moving towards enemy
            score += 100
        score += self.food_rewards.get(loc, 0)
        for hill in self.enemy_hills:
            score += self.hill_rewards[hill].get(loc, 0)
        return score

    def recursive_evaluate(self, warrior, curr_loc, depth, evaluate):
        battleradius2 = self.depthwise_radius2[depth]
        scores = dict([(i, evaluate(warrior, curr_loc, i, battleradius2)) for i in ('n', 'w', 's', 'e', 'o')]) 
        if not depth:
            return scores
        else:
            for d in scores.keys():
                next_loc = self.new_loc(curr_loc, i)
                child_scores = self.recursive_evaluate(warrior, next_loc, depth - 1, evaluate).values()
                #if child_scores:
                #    scores[d] += sum(child_scores)/len(child_scores)
                scores[d] += max(child_scores)
                #child_scores = sorted(self.recursive_evaluate(warrior, next_loc, evaluated, depth - 1, evaluate).values())
                #if child_scores[0] < 0:
                #    scores[d] += child_scores[0]
                #else:
                #    scores[d] += child_scores[-1]
        #evaluated[(warrior, curr_loc)] = scores
        return scores

    def fight(self, my_warrior, lookahead, evaluation_func):
        scores = self.recursive_evaluate(my_warrior, my_warrior, lookahead, evaluation_func)
        #getLogger().debug("WARRIOR: (%d, %d), scores: %s" % (my_warrior/self.cols, my_warrior%self.cols, scores))
        sorted_dirs = sorted(scores.keys(), key=scores.get, reverse=True)
        return self.try_move(my_warrior, sorted_dirs)
        for d in sorted_dirs:
            if self.do_move(my_warrior, d):
                self.available_ants.pop(my_warrior)
                break

    def random_explore(self, loc):
        next_dirs = {
                'n' : (('w', 'e', 's'), ('e', 'w', 's')),
                's' : (('w', 'e', 'n'), ('e', 'w', 'n')),
                'e' : (('n', 's', 'w'), ('s', 'n', 'w')),
                'w' : (('n', 's', 'e'), ('s', 'n', 'w'))
                }
        dir = self.my_ants[loc].prev_dir
        if not dir:
            dir = ('n', 's', 'e', 'w')[random.randint(0, 3)]
        if self.do_move(loc, dir):
            self.my_ants[loc].prev_dir = dir
            self.available_ants.pop(loc)
            return True
        dirs = next_dirs[dir][random.randint(0, 1)]
        for dir in dirs:
            next_loc = self.new_loc(loc, dir)
            for k, v in self.hill_rewards.iteritems():
                v[next_loc] = self.compute_qvalue(next_loc, v)
            if self.do_move(loc, dir):
                self.my_ants[loc].prev_dir = dir
                self.available_ants.pop(loc)
                return True
        return False

    def defend(self):
        self.defenders.clear()
        hill_defenders = dict([(i, 0) for i in self.my_hills])
        hill_watchmen = dict([(i, 0) for i in self.my_hills])
        for ant in self.available_ants.keys():
            for hill in hill_defenders.keys():
                if hill_defenders[hill] >= self.defender_cnt:
                    break
                if self.defenders.has_key(ant) or self.watchmen.has_key(ant):
                    break

                #if self.distance_sq(ant, hill) < 4*self.viewradius2:
                if self.distance_sq(ant, hill)  <= 4*self.attackradius2:
                    if self.my_warriors.has_key(ant):
                        scores = self.recursive_evaluate(ant, ant, 0, self.heuristic_evaluate)
                        #getLogger().debug("DEFENDER: (%d, %d), scores: %s" % (ant/self.cols, ant%self.cols, scores))
                        sorted_dirs = sorted(scores.keys(), key=scores.get, reverse=True)
                    else:
                        sorted_dirs = ['n', 'w', 's', 'e']
                        random.shuffle(sorted_dirs)
                    for d in sorted_dirs:
                        new_loc = self.new_loc(ant, d)
                        if self.distance_sq(new_loc, hill) > 4*self.attackradius2:
                            continue
                        if self.my_hill_distance[hill].get(new_loc, self.compute_distance(new_loc, self.my_hill_distance[hill])) < 2:
                        #if new_loc == hill:
                            continue
                        if self.do_move(ant, d):
                            self.available_ants.pop(ant)
                            hill_defenders[hill] += 1
                            self.defenders[ant] = 1
                            break
            for hill in hill_watchmen.keys():
                if hill_watchmen[hill] >= self.watchmen_cnt:
                    break
                if self.defenders.has_key(ant) or self.watchmen.has_key(ant):
                    break

                #if self.distance_sq(ant, hill) < 4*self.viewradius2:
                if self.distance_sq(ant, hill)  <= self.attackradius2:
                    if self.my_warriors.has_key(ant):
                        scores = self.recursive_evaluate(ant, ant, 0, self.heuristic_evaluate)
                        #getLogger().debug("DEFENDER: (%d, %d), scores: %s" % (ant/self.cols, ant%self.cols, scores))
                        sorted_dirs = sorted(scores.keys(), key=scores.get, reverse=True)
                    else:
                        sorted_dirs = ['n', 'w', 's', 'e', 'o']
                        random.shuffle(sorted_dirs)
                    for d in sorted_dirs:
                        new_loc = self.new_loc(ant, d)
                        if self.distance_sq(new_loc, hill) > self.attackradius2:
                            continue
                        #if new_loc == hill:
                        if self.my_hill_distance[hill].get(new_loc, self.compute_distance(new_loc, self.my_hill_distance[hill])) < 2:
                            continue
                        if self.do_move(ant, d):
                            self.available_ants.pop(ant)
                            hill_watchmen[hill] += 1
                            self.watchmen[ant] = 1
                            break

                    

    def do_turn(self):
        self.food.update(self.new_food)
        for loc in self.food.keys():
            if self.visible.has_key(loc) and not self.new_food.has_key(loc):
                self.food.pop(loc)
                self.map_data[loc] = LAND
        self.orders.clear()
        self.deferred_moves = {}
        self.available_ants.update(self.my_ants)
        self.update_visible()
        for hill in self.my_hills:
            if not self.my_hill_distance.has_key(hill):
                self.my_hill_distance[hill] = {hill : 0}

        for hill in self.enemy_hills[:]:
            if self.map_data[hill] != ENEMY_HILL:
                self.enemy_hills.remove(hill)
                self.map_data[hill] = LAND
                self.hill_rewards.pop(hill)

#self.explore_targets = [i for i in self.unvisited_milestones.keys() if self.visible.has_key(i)]
        self.explore_targets = [i for i in self.unvisited_milestones.keys() if self.seen_milestones.has_key(i)]
        getLogger().debug("Explore targets.........")
        getLogger().debug(self.explore_targets)
        getLogger().debug("Explore targets: %s" % str(self.explore_targets))
        self.update_MDP()

        self.defender_cnt = 0
        self.watchmen_cnt = 0
        explore = self.explore
#explore = self.explore_milestones
        self.update_battle_clusters()
        if random.randint(0, 99) < 95:
            evaluate = self.heuristic_evaluate
        else:
            evaluate = self.greedy_evaluate
        if len(self.my_ants) < 3:
            evaluate = self.escape_evaluate
        elif len(self.my_hills) < 3:
            if 15 < len(self.my_ants) <= 20:
                self.watchmen_cnt = 1
            if 20 < len(self.my_ants) <= 30:
                self.watchmen_cnt = 2
            elif 30 < len(self.my_ants) <= 50:
                self.watchmen_cnt = 2
                self.defender_cnt = 3
            elif 50 < len(self.my_ants) <= 100:
                self.watchment_cnt = 2
                self.defender_cnt = 8
            elif 100 < len(self.my_ants) <= 150:
                self.defender_cnt = 10
                self.watchmen_cnt = 4
            elif 150 < len(self.my_ants) <= 200:
                self.defender_cnt = 20
                self.watchmen_cnt = 4
            elif len(self.my_ants) > 200:
                self.defender_cnt = 40
                self.watchmen_cnt = 4
        if len(self.my_ants) > 200:
            explore = self.random_explore

        self.defend()

        warrior_list = sorted(self.my_warriors.keys(), key=lambda x: len(self.my_warriors[x]))
        for ant in warrior_list:
            if self.defenders.has_key(ant) or self.watchmen.has_key(ant):
                continue
            self.fight(ant, 0, evaluate)
        for ant in self.available_ants.keys():
            if self.gather(ant):
                continue
        for ant in self.available_ants.keys():
            explore(ant)

        cnt = 0
        changed = True
        while changed:
            changed = False
            for ant in self.deferred_moves.keys():
                for d in self.deferred_moves[ant]:
                    if self.do_move(ant, d):
                        self.deferred_moves.pop(ant)
                        changed = True
                        break
#if cnt >= 10:
#break
            cnt += 1
        self.deferred_moves.clear()
        self.cleanup()

if __name__ == '__main__':
    e = Engine()
    e.rows = 60
    e.cols = 90
    e.attackradius2 = 5
    e.do_setup()

    def _idx_from_loc(row, col):
        return row*e.cols + col

    def _loc_from_idx(idx):
        return idx/e.cols, idx/e%cols

    def _test_distance():
        loc1 = _idx_from_loc(21, 84)
        loc2 = _idx_from_loc(20, 80)
        dt = e.distance_sq(loc1, loc2)
        assert dt == 17, "You moron! Fix the distance calculator. Is 1^ + 4^ = " + str(dt) + "?"
    _test_distance()
