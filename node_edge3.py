import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
import numpy as np
from sklearn.cluster import AgglomerativeClustering

# ファイルパスの指定
centerline_path = r"C:\szok\szoksrg_simulation\szoksrg_road_split_with_all_attributes.geojson"
output_node_path = r"C:\szok\szoksrg_simulation\szoksrg_nodes.shp"
output_edge_path = r"C:\szok\szoksrg_simulation\szoksrg_edges.shp"

# 道路中心線の読み込み
roads = gpd.read_file(centerline_path, encoding="utf-8")
if roads.empty:
    print("道路ラインが読み込めませんでした。パスやファイルを確認してください。")
    import sys
    sys.exit()

# ノードとエッジのデータを格納する変数
temp_coords = []       # 始点・終点の座標を都度追加
coord_indices = []     # 始点・終点のインデックス
edge_attributes = []   # エッジの属性

edge_id_counter = 1

for _, row in roads.iterrows():
    geom = row.geometry
    car_access_raw = row.get("car_access", False)
    ped_access_raw = row.get("ped_access", False)
    route_id_raw = row.get("路線ID", None)
    road_width_raw = row.get("道路幅", None)
    max_width_raw = row.get("max_width", None)

    # データ型を適切に変換
    car_access_val = bool(car_access_raw)
    ped_access_val = bool(ped_access_raw)
    route_id_val = str(route_id_raw) if route_id_raw is not None else None
    road_width_val = float(road_width_raw) if road_width_raw is not None else None
    max_width_val = float(max_width_raw) if max_width_raw is not None else None

    if isinstance(geom, MultiLineString):
        lines = geom.geoms
    elif isinstance(geom, LineString):
        lines = [geom]
    else:
        continue

    for line in lines:
        if line.is_empty:
            continue

        # --- 修正ポイント: 事前に始点・終点が正しい座標かチェック ---
        start_xy = line.coords[0]
        end_xy = line.coords[-1]

        # None や 2次元以外の座標を持つ場合はスキップ
        if (start_xy is None or len(start_xy) != 2) or (end_xy is None or len(end_xy) != 2):
            continue

        start_idx = len(temp_coords)
        temp_coords.append(start_xy)

        end_idx = len(temp_coords)
        temp_coords.append(end_xy)

        # エッジ属性を追加
        edge_attributes.append({
            "edge_id": edge_id_counter,
            "路線ID": route_id_val,
            "道路幅": road_width_val,
            "max_width": max_width_val,
            "car_access": car_access_val,
            "ped_access": ped_access_val,
            "length": line.length,
            "geometry": line
        })
        coord_indices.append((start_idx, end_idx))

        edge_id_counter += 1

# --- 修正ポイント: 後から temp_coords を再フィルタリングする処理は削除 ---
# ここに "temp_coords = [coord for coord in temp_coords if ...]" といったコードは書かない

# numpy配列に変換
coords_array = np.array(temp_coords)

# クラスタリング
clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=1.0, linkage='complete').fit(coords_array)
labels = clustering.labels_

# ノード作成
cluster_dict = {}
for i, cluster_id in enumerate(labels):
    cluster_dict.setdefault(cluster_id, []).append(coords_array[i])

new_node_records = []
cluster_id_to_node_id = {}
new_node_id_counter = 1

for cluster_id, group_coords in cluster_dict.items():
    arr = np.array(group_coords)
    cx = arr[:, 0].mean()
    cy = arr[:, 1].mean()

    new_node_records.append({
        "node_id": new_node_id_counter,
        "X": cx,
        "Y": cy,
        "geometry": Point(cx, cy)
    })
    cluster_id_to_node_id[cluster_id] = new_node_id_counter
    new_node_id_counter += 1

node_gdf = gpd.GeoDataFrame(new_node_records, crs=roads.crs)

# エッジの作成
edge_records = []
for i, edge_attr in enumerate(edge_attributes):
    edge_id = edge_attr["edge_id"]
    line_geom = edge_attr["geometry"]

    # coord_indices[i] に対応する始点・終点を取得
    start_idx, end_idx = coord_indices[i]

    start_cluster = labels[start_idx]
    end_cluster = labels[end_idx]
    start_node_id = cluster_id_to_node_id[start_cluster]
    end_node_id = cluster_id_to_node_id[end_cluster]

    edge_records.append({
        "edge_id": edge_id,
        "start_node": start_node_id,
        "end_node": end_node_id,
        "length": edge_attr["length"],
        "route_id": edge_attr["路線ID"],
        "道路幅": edge_attr["道路幅"],
        "max_width": edge_attr["max_width"],
        "car_access": edge_attr["car_access"],
        "ped_access": edge_attr["ped_access"],
        "geometry": line_geom
    })

edge_gdf = gpd.GeoDataFrame(edge_records, crs=roads.crs)

# 保存
node_gdf.to_file(output_node_path, driver="ESRI Shapefile", encoding="utf-8")
edge_gdf.to_file(output_edge_path, driver="ESRI Shapefile", encoding="utf-8")

print("ノードとエッジを出力しました。")
