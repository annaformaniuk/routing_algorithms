from collections import deque, namedtuple
import json
import time
import pickle

# we'll use infinity as a default distance to nodes.
inf = float('inf')
Edge = namedtuple('Edge', 'start, end, cost')

print("Program Started at " + str(time.time()))


def make_edge(start, end, cost=1):
    return Edge(start, end, cost)


def createGraphFromGeojson(node_file="selected_nodes.geojson",
                           edge_file='selected_nodes.geojson'):
        t1 = time.time()
        with open(edge_file, "r") as read_file:
            edges_json = json.load(read_file)
            edges = edges_json["features"]

        with open(node_file, "r") as read_file:
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
        with open('graph.json', 'w') as outfile:
            json.dump(g, outfile)
        return g
        # create the network


class Graph:
    # graph.pickle is the saved graph, if it doesn't exist new one is created
    # from the geojson files.
    def __init__(self, edges=[], landmarks={}, config={}):
        # let's check that the data is right
        wrong_edges = [i for i in edges if len(i) not in [2, 3]]
        if wrong_edges:
            raise ValueError('Wrong edges data: {}'.format(wrong_edges))

        self.edges = edges = [Edge(*edge) for edge in edges]
        self.vertices = {e.start for e in edges} | {e.end for e in edges}
        self.landmarks = landmarks
        self.config = config
        self.result = {}

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

    def dijkstra(self, source, dest):
        assert source in self.vertices, 'Such source node doesn\'t exist'
        distances = {vertex: inf for vertex in self.vertices}
        previous_vertices = {
            vertex: None for vertex in self.vertices
        }
        distances[source] = 0
        vertices = self.vertices.copy()
        neighbours = {vertex: set() for vertex in self.vertices}
        removedvertices = []

        for start, end, cost in self.edges:
            neighbours[start].add((end, cost))
        while vertices:
            current_vertex = min(
                vertices, key=lambda vertex: distances[vertex])

            for neighbour, cost in neighbours[current_vertex]:
                alternative_route = distances[current_vertex] + cost
                if alternative_route < distances[neighbour]:
                    distances[neighbour] = alternative_route
                    previous_vertices[neighbour] = current_vertex
            if distances[current_vertex] == inf or current_vertex == dest:
                break
            vertices.remove(current_vertex)
            removedvertices.append(current_vertex)

        path, current_vertex = deque(), dest
        while previous_vertices[current_vertex] is not None:
            path.appendleft(current_vertex)
            current_vertex = previous_vertices[current_vertex]
        if path:
            path.appendleft(current_vertex)
        self.result["path"] = path
        self.result["removedvertices"] = removedvertices
        return self

    def dijkstra_landmark(self, source, dest):
        assert source in self.vertices, 'Such source node doesn\'t exist'
        distances = {vertex: inf for vertex in self.vertices}
        previous_vertices = {
            vertex: None for vertex in self.vertices
        }
        distances[source] = 0
        vertices = self.vertices.copy()
        neighbours = {vertex: set() for vertex in self.vertices}
        removedvertices = []

        for start, end, cost in self.edges:
            neighbours[start].add((end, cost))
        while vertices:
            current_vertex = min(
                vertices, key=lambda vertex: distances[vertex])

            for neighbour, cost in neighbours[current_vertex]:
                if int(current_vertex) in self.landmarks:
                    # cost -= cost
                    # no cost to move to a landmark favored node, best results
                    # till now, not useful if lots of small edges
                    # cost -= self.landmarks[int(current_vertex)]
                    # highly biased towards landwarks, sometimes doesn't give
                    # result when discount setting is high
                    cost /= 0.5 * cost
                    # print cost
                alternative_route = distances[current_vertex] + cost
                if alternative_route < distances[neighbour]:
                    distances[neighbour] = alternative_route
                    previous_vertices[neighbour] = current_vertex
            if distances[current_vertex] == inf or current_vertex == dest:
                break
            vertices.remove(current_vertex)
            removedvertices.append(current_vertex)

        path, current_vertex = deque(), dest
        while previous_vertices[current_vertex] is not None:
            path.appendleft(current_vertex)
            current_vertex = previous_vertices[current_vertex]
        if path:
            path.appendleft(current_vertex)
        self.result["path"] = path
        self.result["removedvertices"] = removedvertices
        return self

    def get_geom_from_path(self):
        with open(self.config['nodes_file'], "r") as read_file:
            nodes_json = json.load(read_file)
            nodes = nodes_json["features"]
        self.result['geom_path'] = []
        for vertex in self.result["path"]:
            for node in nodes:
                if(node["properties"]["nodeID"] == int(vertex)):
                    self.result['geom_path'].append(
                        node["geometry"]["coordinates"])
        return self

    def to_geojson(self):
        return '{"type": "FeatureCollection","crs": { \
            "type": "name", "properties": { "name": \
                "urn:ogc:def:crs:EPSG::25832" } },"features": \
                    [{"type": "Feature","properties":{"e":"m"},"geometry": \
                        {"type": "LineString","coordinates":'+str(
                            self.result['geom_path'])+'}}]}'
