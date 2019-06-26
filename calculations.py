from math import radians, cos, sin, asin, sqrt


def UTM_to_lb(lat, lon, alt):
    input_string = '     {}      {}      {} '.format(lat, lon, alt)
    text_file = open("LB2.txt", "w")
    text_file.write(input_string)
    text_file.close()
    os.environ["PROJ_LIB"] = "C:/PROJSHARE"  # !!!!!
    os.system(
        '"cs2cs.exe +init=epsg:25832 +to +init=epsg:4326 < LB2.txt > PC2.txt"')
    with open('PC2.txt', encoding='utf8') as f:
        output = f.read().strip().split()
        return output[0], output[1]


def haversine(coord1, coord2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """

    (lat1, lon1) = coord1
    (lat2, lon2) = coord2
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    # returns in km
    return c * r


def get_closest_node(point, nodes):
    node_id = 0
    min_dist = 9999
    for node in nodes:
        (node_lon, node_lat) = node["geometry"]["coordinates"]
        dist = haversine(node_lon, node_lat, point[1], point[0])
        # print(dist)
        if (dist < min_dist):
            min_dist = dist
            node_id = node["properties"]["nodeID"]
    return node_id, min_dist


def distance(a, b):
    return sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)


def is_between(a, c, b, deviation):
    dif = haversine(a, c) + haversine(c, b) - haversine(a, b)
    return dif < deviation


def find_node_objects(ids, nodes):
    # print(ids)
    # print(len(nodes))
    node_objects = []
    for single_id in ids:
        for node in nodes:
            if (str(node["properties"]["nodeID"]) == single_id):
                node_objects.append(node)
    return node_objects


def sum_route_length(route):
    length = 0
    for edge in route:
        length += edge["properties"]["length"]
    return length
