
def get_move_sequences(moves, lanes, same_prio):
    """
    Returns:
    (list): list of independent moves sequences.
    (dict): dictionary where move index points to a list
    of other moves indices that it depends on. 
    """
    if len(moves) == 0:
        return [], dict()
    item_groups = get_item_groups(moves, lanes)

    if same_prio:
        depends_on = construct_dependency_graph_same_prio(moves, item_groups)
    else:
        depends_on = construct_dependency_graph(moves, item_groups)

    move_trees = []  # happen to be the move sequences; indices of moves that are connected components within graph

    for i in range(len(moves)):
        if len(depends_on[i]) == 0:
            move_trees.append([i])
        else:
            to_merge = set()
            for dependency in depends_on[i]:
                for t in range(len(move_trees)):
                    if dependency in move_trees[t]:
                        to_merge.add(t)
                        break
            to_merge = list(to_merge)
            for t in to_merge[1:]:
                move_trees[to_merge[0]].extend(move_trees[t])
            move_trees[to_merge[0]].append(i)
            move_trees = [move_trees[t] for t in range(len(move_trees)) if not t in to_merge[1:]]

    return move_trees, depends_on


def construct_dependency_graph(moves, item_groups):
    """
    Creates a dictionary where move index points to a list
    of other moves indices that it depends on.
    """
    depends_on = {i: [] for i in range(len(moves))}
    for i in range(len(moves)):
        from_lane = moves[i][0]
        to_lane = moves[i][1]
        for j in range(i + 1, len(moves)):
            if from_lane == moves[j][0]:
                if item_groups[i] == item_groups[j]:
                    continue
                else:
                    depends_on[j].append(i)
                    break
            elif from_lane == moves[j][1]:
                depends_on[j].append(i)
                break
        for j in range(i + 1, len(moves)):
            if to_lane == moves[j][1]:
                if item_groups[i] == item_groups[j]:
                    continue
                else:
                    depends_on[j].append(i)
                    break
            elif to_lane == moves[j][0]:
                depends_on[j].append(i)
                break

    return depends_on


def construct_dependency_graph_same_prio(moves, item_groups):
    """
        Creates a dictionary where move index points to a list
        of other moves indices that it depends on.
        """
    depends_on = {i: [] for i in range(len(moves))}
    for i in range(len(moves)):
        from_lane = moves[i][0]
        to_lane = moves[i][1]
        for j in range(i + 1, len(moves)):
            if from_lane == moves[j][0]:
                if item_groups[i] == item_groups[j]:
                    depends_on[j].append(i)
                    break
                else:
                    continue
            elif from_lane == moves[j][1]:
                if item_groups[i] == item_groups[j]:
                    depends_on[j].append(i)
                    break
        for j in range(i + 1, len(moves)):
            if to_lane == moves[j][1]:
                if item_groups[i] == item_groups[j]:
                    depends_on[j].append(i)
                    break
                else:
                    continue

            elif to_lane == moves[j][0]:
                if item_groups[i] == item_groups[j]:
                    depends_on[j].append(i)
                    break

    return depends_on


def get_item_groups(moves: list, lanes: list):
    """
    list of priority groups that are moved starting with first move until the last
    """
    groups = []
    new_lanes = lanes.copy()
    for move in moves:
        from_lane = move[0]
        to_lane = move[1]
        new_from_lane, item_group = new_lanes[from_lane].remove_load()
        new_to_lane = new_lanes[to_lane].add_load(item_group)
        new_lanes[from_lane] = new_from_lane
        new_lanes[to_lane] = new_to_lane
        groups.append(item_group)
    return groups


def get_dependencies(moves, lanes):
    dependencies_dict = {"unequal_prio":
        {
            "start-start": [],
            "start-end": [],
            "end-start": [],
            "end-end": [],
        },
        "equal_prio":
            {
                "start-start": [],
                "start-end": [],
                "end-start": [],
                "end-end": [],
            }
    }

    if len(moves) == 0:
        return dependencies_dict

    item_groups = get_item_groups(moves, lanes)

    for i in range(0, len(moves)):
        for j in range(i, len(moves)):
            if i != j:
                if moves[i][1] == moves[j][0]:
                    # end-start
                    if item_groups[i] != item_groups[j]:
                        dependencies_dict["unequal_prio"]["end-start"].append([i, j])
                    else:
                        dependencies_dict["equal_prio"]["end-start"].append([i, j])

                if moves[i][0] == moves[j][1]:
                    # start-end
                    if item_groups[i] != item_groups[j]:
                        dependencies_dict["unequal_prio"]["start-end"].append([i, j])
                    else:
                        dependencies_dict["equal_prio"]["start-end"].append([i, j])

                if moves[i][0] == moves[j][0]:
                    # start-start
                    if item_groups[i] != item_groups[j]:
                        dependencies_dict["unequal_prio"]["start-start"].append([i, j])
                    else:
                        dependencies_dict["equal_prio"]["start-start"].append([i, j])

                if moves[i][1] == moves[j][1]:
                    # end-end
                    if item_groups[i] != item_groups[j]:
                        dependencies_dict["unequal_prio"]["end-end"].append([i, j])
                    else:
                        dependencies_dict["equal_prio"]["end-end"].append([i, j])

    return dependencies_dict
