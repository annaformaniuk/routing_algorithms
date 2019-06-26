import sys
import json
from dijkstra import Graph
from calculations import is_between, find_node_objects, sum_route_length
from calculations import haversine


def create_graph(nodes, edges, simple):
    temp = []
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
                # twice to be bidirectional
                temp.append(
                    (str(start), str(end), edge["properties"]["length"]))
                temp.append(
                    (str(end), str(start), edge["properties"]["length"]))
    else:
        # with landmarks
        for edge in edges:
            e_one = (edge["geometry"]["coordinates"][0][0][1],
                     edge["geometry"]["coordinates"][0][0][0])
            e_two = (edge["geometry"]["coordinates"][0][-1][1],
                     edge["geometry"]["coordinates"][0][-1][0])
            score = edge["properties"]["length"]
            for landmark in landmarks:
                l = (landmark["geometry"]["coordinates"][1],
                     landmark["geometry"]["coordinates"][0])
                influence_radius = landmark[
                    "properties"]["height_norm (0.1)"]/10
                if (is_between(e_one, l, e_two, influence_radius)):
                    # if (landmark["properties"]["name"] ==
                    #    'Kath. Church Holy Cross\" in Munster\"'):
                    #     print("church", edge["properties"]["streetID"])
                    score = score*((1-landmark["properties"]["TOTAL_SCORE"])/1)
                    if (score < 0):
                        score = 0

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
                temp.append((str(start), str(end), score))
                temp.append((str(end), str(start), score))

    # create the network
    graph = Graph(temp)
    return graph


def find_corresponding_nodes(nodes, edges, point):
    # look for the nodes that are on the street segment, the point is on
    # (just the closest node might not be on the same street)
    for edge in edges:
        one_side = (edge["geometry"]["coordinates"][0][0][1],
                    edge["geometry"]["coordinates"][0][0][0])
        other_side = (edge["geometry"]["coordinates"][0][-1][1],
                      edge["geometry"]["coordinates"][0][-1][0])
        # possible nodes for the origin point
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
    routes_nodes = []
    routes_edges = []
    minimal = {"route": [], "route_dist": 9999999}

    # find the shortest route among the four, taking into account the
    # distance from the start point to the start node
    # and from end node to the end point
    for j, route_obj in enumerate(routes):
        route = route_obj
        route_nodes = find_node_objects(route, nodes)
        routes_nodes.append(route_nodes)
        route_edges = []
        for i, route_node in enumerate(route_nodes):
            if (i != len(route_nodes)-1):
                for edge in edges:
                    if (((edge["geometry"]["coordinates"][0][0] ==
                        route_nodes[i]["geometry"]["coordinates"]) &
                        (edge["geometry"]["coordinates"][0][-1] ==
                        route_nodes[i+1]["geometry"]["coordinates"])) |
                        ((edge["geometry"]["coordinates"][0][0] ==
                         route_nodes[i+1]["geometry"]["coordinates"]) &
                        (edge["geometry"]["coordinates"][0][-1] ==
                         route_nodes[i]["geometry"]["coordinates"]))):
                        route_edges.append(edge)
        routes_edges.append(route_edges)
        route_dist = sum_route_length(route_edges)
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

    # append the path from the start point to start node
    minimal["route"].append(
        {"type": "Feature",
         "properties": {
             "name": "origin"},
         "geometry": {"type": "MultiLineString",
                      "coordinates": [
                          [[start_point[1], start_point[0]],
                           node_combinations[chosen_route_id][0]["geometry"][
                                "coordinates"]]]}})

    # append the path from the end node to the end point
    minimal["route"].append(
        {"type": "Feature",
         "properties": {
             "name": "dest"},
         "geometry": {"type": "MultiLineString",
                      "coordinates": [
                          [[end_point[1], end_point[0]],
                           node_combinations[chosen_route_id][1]["geometry"][
                                "coordinates"]]]}})

    return minimal


if (__name__ == "__main__"):
    rewe = [51.968069, 7.622946]
    brewery = [51.972735, 7.628477]
    theater = [51.971236, 7.613781]
    edeka = [51.971235, 7.640843]
    points = []

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

    # read the edges and the nodes
    with open("inputs/selected_edges_wgs84.geojson", "r") as read_file:
        edges_json = json.load(read_file)
        edges = edges_json["features"]

    with open("inputs/selected_nodes_wgs84.geojson", "r") as read_file:
        nodes_json = json.load(read_file)
        nodes = nodes_json["features"]

    with open("inputs/landmarks_wave4_ratings_height.geojson", "r",
              encoding="utf8") as rf:
        landmarks_json = json.load(rf)
        landmarks = landmarks_json["features"]

    simple = sys.argv[3] == "simple"
    # build the graph
    graph = create_graph(nodes, edges, simple)

    # find which streets the points belong to
    one_side_node_start, other_side_node_start = find_corresponding_nodes(
        nodes, edges, start_point)
    one_side_node_end, other_side_node_end = find_corresponding_nodes(
        nodes, edges, end_point)

    # print results
    print(one_side_node_start, other_side_node_start,
          one_side_node_end, other_side_node_end)

    # for future geojson file
    node_combinations = [find_node_objects([one_side_node_start,
                                            one_side_node_end], nodes),
                         find_node_objects([other_side_node_start,
                                            other_side_node_end], nodes),
                         find_node_objects([one_side_node_start,
                                            other_side_node_end], nodes),
                         find_node_objects([other_side_node_start,
                                            one_side_node_end], nodes)]

    # find possible routes
    routes = []
    routes.append(graph.dijkstra(one_side_node_start, one_side_node_end))
    routes.append(graph.dijkstra(other_side_node_start, other_side_node_end))
    routes.append(graph.dijkstra(one_side_node_start, other_side_node_end))
    routes.append(graph.dijkstra(other_side_node_start, one_side_node_end))

    # find and save the shortest one
    minimal = find_shortest_route(routes, nodes, start_point, end_point)

    filename = 'outputs/{0}_{1}_{2}.geojson'.format(
        sys.argv[1], sys.argv[2], sys.argv[3])

    with open(filename, 'w') as file:
        json.dump(
            {'type': "FeatureCollection", "features": minimal["route"]}, file)
