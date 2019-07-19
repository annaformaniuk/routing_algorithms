import sys
import os
import json
from dijkstra import Graph
from calculations import is_between, find_node_objects, sum_route_length
from calculations import haversine


def create_graph(nodes, edges, simple):
    """
    Creates a graph of nodes and distances between them,
    that is then being used to calculate routes and returns it
    @args:
        nodes: objects read from a geojson
        edges: objects read from another geojson
        simple: boolean of whether it's a shortest path (True)
                of influenced by landmarks (False)
    """
    temp = []
    # if it's a Graph for the shortest path algorithm:
    if simple:
        # find nodes that are on the opposite sides of road segments
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
                # append nodes with distances to the Graph
                # twice for it to be bidirectional
                temp.append(
                    (str(start), str(end), edge["properties"]["length"]))
                temp.append(
                    (str(end), str(start), edge["properties"]["length"]))
    else:
        # if it's a Graph for the algorithm that considers landmarks
        for edge in edges:
            # look at the edges at first
            # first and last coordinate pair, because sometimes they have
            # multiple points in between
            e_one = (edge["geometry"]["coordinates"][0][0][1],
                     edge["geometry"]["coordinates"][0][0][0])
            e_two = (edge["geometry"]["coordinates"][0][-1][1],
                     edge["geometry"]["coordinates"][0][-1][0])
            # take the length to calculate the cost of the edge
            score = edge["properties"]["length"]
            for landmark in landmarks:
                # if any landmark is also on that street
                l = (landmark["geometry"]["coordinates"][1],
                     landmark["geometry"]["coordinates"][0])
                # or even just close to the street if it's a particularly heigh
                # building, like the Holy Cross Church in Kreuzviertel area
                influence_radius = landmark[
                    "properties"]["height_norm (0.1)"]/10
                # then decrease the cost of the edge by the score of its
                # popularity with an increased infulence by a factor of 1.5
                if (is_between(e_one, l, e_two, influence_radius)):
                    score = score*(
                        (1-landmark["properties"]["TOTAL_SCORE"])/1.5)
                    if (score < 0):
                        score = 0

            # then find nodes that are on opposite sides of those edges
            start, end = None, None
            for node in nodes:
                if (node["geometry"]["coordinates"] ==
                        edge["geometry"]["coordinates"][0][0]):

                    start = node["properties"]["nodeID"]
                if (node["geometry"]["coordinates"] ==
                        edge["geometry"]["coordinates"][0][-1]):

                    end = node["properties"]["nodeID"]

            if (start is not None) & (end is not None):
                # and feed them to the Graph
                # twice to be bidirectional
                temp.append((str(start), str(end), score))
                temp.append((str(end), str(start), score))

    # create the network from the nodes' ids and costs of movement
    # between them
    graph = Graph(temp)
    return graph


def find_corresponding_nodes(nodes, edges, point):
    """
    Look for the nodes that are on the street segment, the point is on
    (just the closest node might not be on the same street)
    @args:
        nodes: objects read from a geojson
        edges: objects read from another geojson
        point: (lat,lon) coordinates of a point
    Returns nodes that are on both sides of the street, since at this point
        we don't know in which direction the destination node is
    """
    for edge in edges:
        one_side = (edge["geometry"]["coordinates"][0][0][1],
                    edge["geometry"]["coordinates"][0][0][0])
        other_side = (edge["geometry"]["coordinates"][0][-1][1],
                      edge["geometry"]["coordinates"][0][-1][0])
        # possible nodes for the point
        if (is_between(one_side, point, other_side, 0.01)):
            one_side_node, other_side_node = None, None
            for node in nodes:
                if (node["geometry"]["coordinates"] ==
                        edge["geometry"]["coordinates"][0][0]):

                    one_side_node = str(node["properties"]["nodeID"])
                if (node["geometry"]["coordinates"] ==
                        edge["geometry"]["coordinates"][0][-1]):

                    other_side_node = str(node["properties"]["nodeID"])

    return one_side_node, other_side_node


def find_shortest_route(routes, nodes, start_point, end_point):
    """
    Finds a shortest path between four possible ones between two points
    The points are given to consider the distance from a point to the node
    the route starts/ends at
    @args:
        routes: a list of routes (each route being a list of node ids)
        nodes: objects read from a geojson
        start_point: (lat,lon) coordinates of a point
        end_point: (lat,lon) coordinates of a point
    """

    routes_nodes = []
    routes_edges = []
    # the minimal distance will be lowered starting from this.
    # the current value might be reconsidered
    minimal = {"route": [], "route_dist": 9999999}

    # iterate through the routes, which contain only node ids
    for j, route_obj in enumerate(routes):
        route = route_obj
        # find their full objects because we need coordinates to find routes
        # and have distances
        route_nodes = find_node_objects(route, nodes)
        routes_nodes.append(route_nodes)
        route_edges = []
        # find the edges
        for i, route_node in enumerate(route_nodes):
            if (i != len(route_nodes)-1):
                for edge in edges:
                    if (((edge["geometry"]["coordinates"][0][0] ==
                        route_nodes[i]["geometry"]["coordinates"]) &
                        (edge["geometry"]["coordinates"][0][-1] ==
                         route_nodes[i+1]["geometry"]["coordinates"]))):
                        route_edges.append(edge)
                    if (((edge["geometry"]["coordinates"][0][0] ==
                        route_nodes[i+1]["geometry"]["coordinates"]) &
                        (edge["geometry"]["coordinates"][0][-1] ==
                         route_nodes[i]["geometry"]["coordinates"]))):
                        reversed_geom = edge
                        reversed_geom["geometry"]["coordinates"][0] = edge[
                            "geometry"]["coordinates"][0][::-1]
                        route_edges.append(reversed_geom)
        routes_edges.append(route_edges)
        # sum the distance between nodes only
        route_dist = sum_route_length(route_edges)
        # then add distances from points to the nodes
        route_dist += haversine(
            start_point, (
                node_combinations[j][0]["geometry"]["coordinates"][1],
                node_combinations[j][0]["geometry"]["coordinates"][0]))*1000
        route_dist += haversine(
            end_point, (
                node_combinations[j][1]["geometry"]["coordinates"][1],
                node_combinations[j][1]["geometry"]["coordinates"][0]))*1000
        print(route_dist)
        if (route_dist < minimal["route_dist"]):
            minimal["route"] = route_edges
            minimal["route_dist"] = route_dist
            chosen_route_id = j

    # find the distance from the node to the point to add it to the geojson
    first_len = haversine(start_point, (
                node_combinations[j][0]["geometry"]["coordinates"][1],
                node_combinations[j][0]["geometry"]["coordinates"][0]))*1000

    # append the path from the start point to start node
    minimal["route"].insert(
        0, {"type": "Feature",
            "properties": {
             "name": "origin-node",
             "length": first_len},
            "geometry": {"type": "MultiLineString",
                         "coordinates": [
                          [[start_point[1], start_point[0]],
                           node_combinations[chosen_route_id][0]["geometry"][
                                "coordinates"]]]}})

    # same for the other side
    second_len = haversine(
            end_point, (
                node_combinations[j][1]["geometry"]["coordinates"][1],
                node_combinations[j][1]["geometry"]["coordinates"][0]))*1000

    # append the path from the end node to the end point
    minimal["route"].append(
        {"type": "Feature",
         "properties": {
             "name": "end-node",
             "length": second_len},
         "geometry": {"type": "MultiLineString",
                      "coordinates": [
                          [node_combinations[chosen_route_id][1]["geometry"][
                                "coordinates"],
                           [end_point[1], end_point[0]]]]}})

    return minimal


if (__name__ == "__main__"):
    # define points needed for the study
    rewe = [51.968069, 7.622946]
    brewery = [51.972735, 7.628477]
    theater = [51.971236, 7.613781]
    edeka = [51.971235, 7.640843]
    points = []

    # find out which points were passed in the terminal
    if ("rewe" in sys.argv):
        points.append(rewe)
    if ("brewery" in sys.argv):
        points.append(brewery)
    if ("theater" in sys.argv):
        points.append(theater)
    if ("edeka" in sys.argv):
        points.append(edeka)

    start_point = points[0]
    end_point = points[1]

    # find out if the shortest path or with landmarks
    simple = sys.argv[3] == "simple"

    current_dir = os.path.dirname(os.path.abspath(__file__))

    # read the edges and the nodes and the landmarks
    with open(current_dir +
              "/inputs/selected_edges_wgs84.geojson", "r") as read_file:
        edges_json = json.load(read_file)
        edges = edges_json["features"]

    with open(current_dir +
              "/inputs/selected_nodes_wgs84.geojson", "r") as read_file:
        nodes_json = json.load(read_file)
        nodes = nodes_json["features"]

    with open(current_dir +
              "/inputs/landmarks_wave4_ratings_height.geojson", "r",
              encoding="utf8") as read_file:
        landmarks_json = json.load(read_file)
        landmarks = landmarks_json["features"]

    # build the graph
    graph = create_graph(nodes, edges, simple)

    # find which streets (and nodes on both sides) the points belong to
    one_side_node_start, other_side_node_start = find_corresponding_nodes(
        nodes, edges, start_point)
    one_side_node_end, other_side_node_end = find_corresponding_nodes(
        nodes, edges, end_point)

    # print results
    print(one_side_node_start, other_side_node_start,
          one_side_node_end, other_side_node_end)

    # find full nodes for future geojson file
    node_combinations = [find_node_objects([one_side_node_start,
                                            one_side_node_end], nodes),
                         find_node_objects([other_side_node_start,
                                            other_side_node_end], nodes),
                         find_node_objects([one_side_node_start,
                                            other_side_node_end], nodes),
                         find_node_objects([other_side_node_start,
                                            one_side_node_end], nodes)]

    # find four possible routes because we have two nodes for each point
    routes = []
    routes.append(graph.dijkstra(one_side_node_start, one_side_node_end))
    routes.append(graph.dijkstra(other_side_node_start, other_side_node_end))
    routes.append(graph.dijkstra(one_side_node_start, other_side_node_end))
    routes.append(graph.dijkstra(other_side_node_start, one_side_node_end))

    # find and save the shortest one
    minimal = find_shortest_route(routes, nodes, start_point, end_point)

    filename = current_dir + '/outputs/{0}_{1}_{2}.geojson'.format(
        sys.argv[1], sys.argv[2], sys.argv[3])

    with open(filename, 'w') as file:
        json.dump(
            {'type': "FeatureCollection", "features": minimal["route"]}, file)
