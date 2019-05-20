from collections import deque, namedtuple
import json
import time
import pickle

# we'll use infinity as a default distance to nodes.
inf = float('inf')
Edge = namedtuple('Edge', 'start, end, cost')


def make_edge(start, end, cost=1):
    return Edge(start, end, cost)


class Graph:
    # graph.pickle is the saved graph, if it doesn't exist new one is created from the geojson files.
    def __init__(self, edges=[]):
        # try:
            # with open('graph.pickle', 'rb') as fp:
                # edges = pickle.load(fp)
            # edges = open('graph.pickle', 'r')
            # Store configuration file values
        # except IOError:
        edges = self.createGraphFromGeojson()
        # let's check that the data is right
        wrong_edges = [i for i in edges if len(i) not in [2, 3]]
        if wrong_edges:
            raise ValueError('Wrong edges data: {}'.format(wrong_edges))

        self.edges = [make_edge(*edge) for edge in edges]

    @property
    def vertices(self):
        return set(
            sum(
                ([edge.start, edge.end] for edge in self.edges), []
            )
        )

    def get_node_pairs(self, n1, n2, both_ends=True):
        if both_ends:
            node_pairs = [[n1, n2], [n2, n1]]
        else:
            node_pairs = [[n1, n2]]
        return node_pairs

    def remove_edge(self, n1, n2, both_ends=True):
        node_pairs = self.get_node_pairs(n1, n2, both_ends)
        edges = self.edges[:]
        for edge in edges:
            if [edge.start, edge.end] in node_pairs:
                self.edges.remove(edge)

    def add_edge(self, n1, n2, cost=1, both_ends=True):
        node_pairs = self.get_node_pairs(n1, n2, both_ends)
        for edge in self.edges:
            if [edge.start, edge.end] in node_pairs:
                return ValueError('Edge {} {} already exists'.format(n1, n2))

        self.edges.append(Edge(start=n1, end=n2, cost=cost))
        if both_ends:
            self.edges.append(Edge(start=n2, end=n1, cost=cost))

    @property
    def neighbours(self):
        neighbours = {vertex: set() for vertex in self.vertices}
        for edge in self.edges:
            neighbours[edge.start].add((edge.end, edge.cost))

        return neighbours

    def dijkstra(self, source, dest):
        assert source in self.vertices, 'Such source node doesn\'t exist'
        distances = {vertex: inf for vertex in self.vertices}
        previous_vertices = {
            vertex: None for vertex in self.vertices
        }
        distances[source] = 0
        vertices = self.vertices.copy()

        while vertices:
            current_vertex = min(
                vertices, key=lambda vertex: distances[vertex])
            vertices.remove(current_vertex)
            if distances[current_vertex] == inf:
                break
            for neighbour, cost in self.neighbours[current_vertex]:
                alternative_route = distances[current_vertex] + cost
                if alternative_route < distances[neighbour]:
                    distances[neighbour] = alternative_route
                    previous_vertices[neighbour] = current_vertex

        path, current_vertex = deque(), dest
        while previous_vertices[current_vertex] is not None:
            path.appendleft(current_vertex)
            current_vertex = previous_vertices[current_vertex]
        if path:
            path.appendleft(current_vertex)
        return path

    def createGraphFromGeojson(self, node_file="selected_nodes.geojson", edge_file="selected_edges.geojson"):
        t1 = time.time()
        with open("selected_edges.geojson", "r") as read_file:
            edges_json = json.load(read_file)
            edges = edges_json["features"]

        with open("selected_nodes.geojson", "r") as read_file:
            nodes_json = json.load(read_file)
            nodes = nodes_json["features"]

        g = []
        for edge in edges:
            start, end = None, None
            for node in nodes:
                if (node["geometry"]["coordinates"] ==
                        edge["geometry"]["coordinates"][0][0]):

                    start = node["properties"]["nodeID"]
                if (node["geometry"]["coordinates"] ==
                        edge["geometry"]["coordinates"][0][-1]):

                    end = node["properties"]["nodeID"]

            if (start is not None) & (end is not None):
                # twice to be bidirectional
                g.append((str(start), str(end), edge["properties"]["length"]))
                g.append((str(end), str(start), edge["properties"]["length"]))
        t2 = time.time()
        print("time to load data", t2-t1)
        with open('graph.pickle', 'wb') as fp:
            pickle.dump(g, fp)
        return g
        # create the network

graph = Graph()


# example of the Graph structure
# graph = Graph([
#     ("a", "b", 7),  ("a", "c", 9),  ("a", "f", 14), ("b", "c", 10),
#     ("b", "d", 15), ("c", "d", 11), ("c", "f", 2),  ("d", "e", 6),
#     ("e", "f", 9)])
t3 = time.time()
# print("time to create graph",t3-t2)
# find a route
# print(graph.dijkstra("5907", "460"))
# t4 = time.time()
# print("time to finf route", t4-t3)

# TODO find the respective coordinates (nodes, edges? what should be the
# return format?
# TODO start and destination points are probably not exactly the nodes
