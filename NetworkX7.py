import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, LineString

# find_nearest_node 関数の修正（孤立ノード処理を削除）
def find_nearest_node(point, nodes):
    """
    指定されたポイントに最も近いノードを検索します。

    Parameters:
        point (shapely.geometry.Point): 検索対象のポイント
        nodes (GeoDataFrame): ノードデータが含まれるGeoDataFrame

    Returns:
        int: 最も近いノードのID
    """
    nodes["distance"] = nodes.geometry.apply(lambda x: point.distance(x))
    nearest_node = nodes.loc[nodes["distance"].idxmin()]
    return nearest_node["node_id"]

# ファイルパスの指定
node_path = r"C:\szok\szoksrg_simulation\szoksrg_nodes.shp"
edge_path = r"C:\szok\szoksrg_simulation\szoksrg_edges.shp"
building_path = r"C:\szok\szoksrg_simulation\szoksrg_plateau_destruction.geojson"
shelter_path = r"C:\szok\import\szoksrg_shelters.shp"
output_route_path = r"C:\szok\szoksrg_simulation\szoksrg_routes.shp"

# 移動速度の設定（km/h）
CAR_SPEED_30KM = 30.0  # 幅員2.5m以上
CAR_SPEED_15KM = 15.0  # 幅員1.5m以上2.5m未満
WALK_SPEED_4_5KM = 4.5  # 幅員0.5m以上1.5m未満

# データの読み込み
nodes = gpd.read_file(node_path, encoding="utf-8")
edges = gpd.read_file(edge_path, encoding="utf-8")
buildings = gpd.read_file(building_path, encoding="utf-8")
shelters = gpd.read_file(shelter_path, encoding="utf-8")

# NetworkXグラフの作成
G = nx.Graph()  # 無向グラフ

# ノードを追加
for _, node in nodes.iterrows():
    G.add_node(node["node_id"], pos=(node.geometry.x, node.geometry.y))

# エッジを追加し、条件に基づく速度を指定
for _, edge in edges.iterrows():
    start_node = edge["start_node"]
    end_node = edge["end_node"]
    road_width = edge["道路幅"]
    max_width_reduction = edge["max_width"]
    car_access = edge['car_access']

    # 幅員条件に基づいて速度を設定
    if road_width - max_width_reduction >= 2.5:
        speed = CAR_SPEED_30KM if car_access == 1 else WALK_SPEED_4_5KM
    elif 1.5 <= road_width - max_width_reduction < 2.5:
        speed = CAR_SPEED_15KM if car_access == 1 else WALK_SPEED_4_5KM
    elif 0.5 <= road_width - max_width_reduction < 1.5:
        speed = WALK_SPEED_4_5KM
    else:
        continue  # 道幅が0.5m未満の場合はエッジを追加しない
    # エッジ幅とcar_accessの判定のデバッグ出力
    # print(f"Edge {start_node}-{end_node}: road_width={road_width}, max_width_reduction={max_width_reduction}, car_access={car_access}, speed={speed}")

    # 移動時間（分単位）= 距離 / 速度 * 60
    time = (edge["length"] / 1000) / speed * 60  # 距離はkm単位、速度はkm/h単位

    # エッジをグラフに追加
    G.add_edge(start_node, end_node, length=edge["length"], time=time, edge_id=edge["edge_id"])

# 各建物から最も近い避難所までのルートを計算
routes = []
route_id = 1  # ルートIDカウンター

for building in buildings.itertuples():
    start_point = building.geometry.centroid
    building_id = building.id
    akiya_flag = building.akiya
    path = None # 未定義変数のエラー回避のためのpath初期化

    # 空き家の場合はルート検索をスキップ
    if akiya_flag:
        routes.append({
            "r_id": route_id,
            "b_id": building_id,
            "akiya": akiya_flag,
            "r_found": False,  # ルートなし
            "n_node": None,
            "p_nodes": None,
            "e_30km": None,
            "e_15km": None,
            "e_4_5km": None,
            "walk_f": False,
            "t_time": None,
            "t_dist": None,
            "geometry": None
        })
        route_id += 1
        continue

    # 建物の出発ノード
    start_node = find_nearest_node(start_point, nodes)

    # 各避難所へのルートと最短距離を求める
    nearest_shelter_node = None
    min_travel_time = float("inf")
    best_path = None
    route_found = False
    is_walking = False  # 徒歩切り替えフラグ

    for shelter in shelters.itertuples():
        shelter_node = find_nearest_node(shelter.geometry, nodes)

        # 最短経路探索
        try:
            path = nx.shortest_path(G, source=start_node, target=shelter_node, weight="time")
            path_edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            travel_time = sum(G[u][v]["time"] for u, v in path_edges)
            route_found = True

            # 現時点で最短の経路を保存
            if travel_time < min_travel_time:
                min_travel_time = travel_time
                nearest_shelter_node = shelter_node
                best_path = path

        except nx.NetworkXNoPath:
            continue

    # ルートデータを保存
    if best_path and len(best_path) > 1:  # ルートが2ノード以上の場合のみ保存
        travel_edges = [(best_path[i], best_path[i + 1]) for i in range(len(best_path) - 1)]

        # 通過エッジIDを速度ごとに分類
        edges_30km, edges_15km, edges_4_5km = [], [], []
        total_length = 0

        for u, v in travel_edges:
            edge_data = G[u][v]
            total_length += edge_data["length"]
            speed = (edge_data["length"] / 1000) / (edge_data["time"] / 60)  # km/h で計算

            # 一度徒歩に切り替わったらその後も徒歩速度に固定
            if is_walking or speed == WALK_SPEED_4_5KM:
                is_walking = True
                edges_4_5km.append(edge_data["edge_id"])
                # print(f"Switching to walking at edge {u}-{v}")
            elif speed == CAR_SPEED_30KM:
                edges_30km.append(edge_data["edge_id"])
            elif speed == CAR_SPEED_15KM:
                edges_15km.append(edge_data["edge_id"])

        # 建物中心から最寄りノードまでのラインを追加
        initial_line = LineString([
            Point(start_point.x, start_point.y),
            Point(*G.nodes[best_path[0]]["pos"])
        ])
        route_line = LineString([Point(*G.nodes[n]["pos"]) for n in best_path])
        complete_route = LineString(list(initial_line.coords) + list(route_line.coords)[1:])

        routes.append({
            "r_id": route_id,  # route_id
            "b_id": building_id,  # building_id
            "akiya": akiya_flag,  # 空き家フラグ
            "r_found": route_found,  # ルートがあるか
            "n_node": start_node,  # 最寄りノード
            "p_nodes": ";".join(map(str, best_path)),  # 通過ノード
            "e_30km": ";".join(map(str, edges_30km)),  # 30kmエッジ
            "e_15km": ";".join(map(str, edges_15km)),  # 15kmエッジ
            "e_4_5km": ";".join(map(str, edges_4_5km)),  # 4.5kmエッジ
            "walk_f": is_walking,  # 徒歩フラグ
            "t_time": min_travel_time,  # 総時間（分）
            "t_dist": total_length,  # 総距離（m）
            "geometry": complete_route,
        })
    else:
        if start_node in G.nodes:
            line_to_node = LineString([
                Point(start_point.x, start_point.y),
                Point(*G.nodes[start_node]["pos"])
            ])
            routes.append({
                "r_id": route_id,
                "b_id": building_id,
                "akiya": akiya_flag,
                "r_found": False,
                "n_node": start_node,
                "p_nodes": None,
                "e_30km": None,
                "e_15km": None,
                "e_4_5km": None,
                "walk_f": False,
                "t_time": None,
                "t_dist": None,
                "geometry": line_to_node,
            })
    route_id += 1

routes_gdf = gpd.GeoDataFrame(routes, crs="EPSG:6676")
routes_gdf.to_file(output_route_path, encoding="utf-8")
print("建物から避難所までの最短ルートが計算され、ルートが保存されました。")
