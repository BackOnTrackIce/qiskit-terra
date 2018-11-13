"""Permutation algorithms for general graphs."""
import logging
import random

import networkx as nx

logger = logging.getLogger(__name__)


class ApproximateTokenSwapper():
    """A class for computing approximate solutions to the Token Swapping problem.

    Internally caches the graph and associated datastructures for re-use."""

    def __init__(self, graph):
        """Construct an ApproximateTokenSwapping object."""
        self.graph = graph
        # We need to fix the mapping from nodes in graph to nodes in shortest_paths.
        # The nodes in graph don't have to integer nor contiguous, but those in a NumPy array are.
        nodelist = list(graph.nodes())
        self.node_map = {node: i for i, node in enumerate(nodelist)}
        self.shortest_paths = nx.floyd_warshall_numpy(graph, nodelist=nodelist)

    def distance(self, node0, node1):
        """Compute the distance between two nodes in `graph`."""
        return self.shortest_paths[self.node_map[node0], self.node_map[node1]]

    def map(self, mapping, trials=4):
        """Perform an approximately optimal Token Swapping algorithm to implement the permutation.

        Supports partial mappings (i.e. not-permutations) for graphs with missing tokens.

        Based on the paper: Approximation and Hardness for Token Swapping by Miltzow et al. (2016)
        ArXiV: https://arxiv.org/abs/1602.05150
        and generalization based on our own work.

        :param mapping: The partial mapping to implement in swaps.
        :param trials: The number of trials to try to perform the mapping. Minimize over the trials.
        :type mapping: Mapping[_V, _V]
        :type trials: int
        :return: Best found list of edges which implement mapping.
        :rtype: List[Swap[_V]]
        """
        tokens = dict(mapping)
        digraph = nx.DiGraph()
        sub_digraph = nx.DiGraph()  # Excludes self-loops in digraph.
        todo_nodes = {node for node, destination in tokens.items() if node != destination}
        for node in self.graph.nodes:
            self._add_token_edges(node, tokens, digraph, sub_digraph)

        trial_results = (list(self._trial_map(digraph.copy(),
                                              sub_digraph.copy(),
                                              todo_nodes.copy(),
                                              tokens.copy()))
                         for _ in range(trials))

        # Once we find a zero solution we stop.
        def take_until_zero(results):
            """Take results until one is emitted of length zero (and also emit that)."""
            for result in results:
                if result:  # Not empty
                    yield result
                else:
                    yield result
                    break

        trial_results = take_until_zero(trial_results)
        return min(trial_results, key=len)

    def _trial_map(self, digraph, sub_digraph, todo_nodes, tokens):
        """Try to map the tokens to their destinations and minimize the number of swaps."""

        def swap(node0, node1):
            """Swap two nodes, maintaining datastructures."""
            self._swap(node0, node1, tokens, digraph, sub_digraph, todo_nodes)

        # Can't just iterate over todo_nodes, since it may change during iteration.
        steps = 0
        while todo_nodes and steps <= 4 * len(self.graph.nodes) ** 2:
            todo_node = random.sample(todo_nodes, 1)[0]

            # Try to find a happy swap chain first by searching for a cycle,
            # excluding self-loops.
            # Note that if there are only unhappy swaps involving this todo_node,
            # then an unhappy swap must be performed at some point.
            # So it is not useful to globally search for all happy swap chains first.
            try:
                cycle = nx.find_cycle(sub_digraph, source=todo_node)
                assert len(cycle) > 1, "The cycle was not happy."
                # We iterate over the cycle in reversed order, starting at the last edge.
                # The first edge is excluded.
                for edge in cycle[-1:0:-1]:
                    yield edge
                    swap(edge[0], edge[1])
                steps += len(cycle) - 1
            except nx.NetworkXNoCycle:
                # Try to find a node without a token to swap with.
                try:
                    edge = next(edge for edge in nx.dfs_edges(sub_digraph, todo_node)
                                if edge[1] not in tokens)
                    # Swap predecessor and successor, because successor does not have a token
                    yield edge
                    swap(edge[0], edge[1])
                    steps += 1
                except StopIteration:
                    # Unhappy swap case
                    cycle = nx.find_cycle(digraph, source=todo_node)
                    assert len(cycle) == 1, "The cycle was not unhappy."
                    unhappy_node = cycle[0][0]
                    # Find a node that wants to swap with this node.
                    predecessor = next(  # pylint: disable=stop-iteration-return
                        predecessor for predecessor in digraph.predecessors(unhappy_node)
                        if predecessor != unhappy_node)
                    yield unhappy_node, predecessor
                    swap(unhappy_node, predecessor)
                    steps += 1
        if todo_nodes:
            raise RuntimeError("Too many iterations while approximating the Token Swaps.")

    def _add_token_edges(self, node, tokens, digraph, sub_digraph):
        """Add diedges to the graph wherever a token can be moved closer to its destination."""
        if node not in tokens:
            return

        if tokens[node] == node:
            digraph.add_edge(node, node)
            return

        for neighbor in self.graph.neighbors(node):
            if self.distance(neighbor, tokens[node]) < self.distance(node, tokens[node]):
                digraph.add_edge(node, neighbor)
                sub_digraph.add_edge(node, neighbor)

    def _swap(self, node1, node2, tokens, digraph, sub_digraph, todo_nodes):
        """Swap two nodes, maintaining the datastructures"""
        assert self.graph.has_edge(node1,
                                   node2), "The swap is being performed on a non-existent edge."
        # Swap the tokens on the nodes, taking into account no-token nodes.
        token1 = tokens.pop(node1, None)
        token2 = tokens.pop(node2, None)
        if token2 is not None:
            tokens[node1] = token2
        if token1 is not None:
            tokens[node2] = token1
        # Recompute the edges incident to node 1 and 2
        for node in [node1, node2]:
            digraph.remove_edges_from([(node, successor) for successor in digraph.successors(node)])
            sub_digraph.remove_edges_from(
                [(node, successor) for successor in sub_digraph.successors(node)])
            self._add_token_edges(node, tokens, digraph, sub_digraph)
            if node in tokens and tokens[node] != node:
                todo_nodes.add(node)
            elif node in todo_nodes:
                todo_nodes.remove(node)