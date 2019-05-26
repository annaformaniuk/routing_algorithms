import json
from dijkstra import Graph
from calculations import is_between, find_node_objects, sum_route_length
from calculations import haversine

# save the edges and the nodes
with open("selected_edges_wgs84.geojson", "r") as read_file:
    edges_json = json.load(read_file)
    edges = edges_json["features"]

with open("selected_nodes_wgs84.geojson", "r") as read_file:
    nodes_json = json.load(read_file)
    nodes = nodes_json["features"]

# find nodes that are on the opposite sides of road segments
temp = []
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
        temp.append((str(start), str(end), edge["properties"]["length"]))
        temp.append((str(end), str(start), edge["properties"]["length"]))

# create the network
graph = Graph(temp)

# define origin and destination points
# start_point = [51.968069, 7.622946]  # rewe
start_point = [51.972735, 7.628477]  # brewery
# end_point = [51.971236, 7.613781]  # theater
end_point = [51.968125, 7.637044]  # garden

# look for the nodes that are on the street segment, the point is on
# (just the closest node might not be on the same street)
for edge in edges:
    one_side = (edge["geometry"]["coordinates"][0][0][1],
                edge["geometry"]["coordinates"][0][0][0])
    other_side = (edge["geometry"]["coordinates"][0][-1][1],
                  edge["geometry"]["coordinates"][0][-1][0])
    # possible nodes for the origin point
    if (is_between(one_side, start_point, other_side)):
        one_side_node_start, other_side_node_start = None, None
        for node in nodes:
            if (node["geometry"]["coordinates"] ==
                    edge["geometry"]["coordinates"][0][0]):

                one_side_node_start = str(node["properties"]["nodeID"])
            if (node["geometry"]["coordinates"] ==
                    edge["geometry"]["coordinates"][0][-1]):

                other_side_node_start = str(node["properties"]["nodeID"])
    # possible nodes for the destination point
    if (is_between(one_side, end_point, other_side)):
        one_side_node_end, other_side_node_end = None, None
        for node in nodes:
            if (node["geometry"]["coordinates"] ==
                    edge["geometry"]["coordinates"][0][0]):

                one_side_node_end = str(node["properties"]["nodeID"])
            if (node["geometry"]["coordinates"] ==
                    edge["geometry"]["coordinates"][0][-1]):

                other_side_node_end = str(node["properties"]["nodeID"])

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


# for fast testing
# routes = [['94', '239', '966', '93', '124', '125', '4818', '877', '5751'
# '955', '979', '255', '249'], ['4983', '4974', '97', '89', '238', '5881',
# '233', '5131', '5216', '5215', '5219', '235', '850', '122', '882', '5739',
# '889'], ['94', '239', '237', '236', '4971', '5206', '92', '864', '991',
# '3192', '882', '5739', '889'], ['4983', '4974', '97', '89', '238', '5881',
# '233', '5131', '5216', '5215', '5219', '235', '850', '122', '882', '948',
# '5749', '249']]

routes_nodes = []
routes_edges = []
minimal = {"route": [], "route_dist": 9999999}

# find the shortest route among the four, taking into account the
# distance from the start point to the start node
# and from end node to the end point
for j, route_obj in enumerate(routes):
    route = route_obj.result["path"]
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
minimal["route"].append({"type": "Feature", "properties": {"name": "origin"},
                        "geometry": {"type": "MultiLineString", "coordinates":
                         [[[start_point[1], start_point[0]],
                          node_combinations[chosen_route_id][0]["geometry"][
                              "coordinates"]]]}})

# append the path from the end node to the end point
minimal["route"].append({"type": "Feature", "properties": {"name": "dest"},
                         "geometry": {"type": "MultiLineString", "coordinates":
                        [[[end_point[1], end_point[0]],
                         node_combinations[chosen_route_id][1]["geometry"][
                             "coordinates"]]]}})

with open('sundayyy.geojson', 'w') as file:
    json.dump(
        {'type': "FeatureCollection", "features": minimal["route"]}, file)
