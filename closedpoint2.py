# 
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import substring

# ファイルパスの指定
road_path = r"C:\szok\import\szoksrg_road.shp"
closed_road_path = r"C:\szok\szoksrg_simulation\szoksrg_road_plateau_area_analysis.geojson"
building_path = r"C:\szok\szoksrg_simulation\szoksrg_plateau_destruction.geojson"
output_path = r"C:\szok\szoksrg_simulation\szoksrg_road_split_with_all_attributes.geojson"

# 道路ポリゴンと建物レイヤーの読み込み
roads = gpd.read_file(road_path, encoding="utf-8")
closed_roads = gpd.read_file(closed_road_path, encoding="utf-8")
buildings = gpd.read_file(building_path, encoding="utf-8")

# is_closedが1のエッジのみを選択
closed_edges = closed_roads[closed_roads["is_closed"] == 1]

# ped_accessが0の道路ポリゴンを選択
no_pedestrian_access_roads = closed_roads[closed_roads["ped_access"] == 0]

# c_build_idを使って削除対象の建物ポリゴンを抽出
target_buildings = buildings[buildings["id"].isin(closed_edges["c_build_id"].str.split(",").explode())]

# 分割後のエッジを格納するリスト
new_edges = []

# 各道路中心線の分割処理
for road in roads.itertuples():
    road_geom = road.geometry
    road_id = road.路線ID  # 道路のID
    attributes = road._asdict()  # 元の属性情報を辞書として取得

    # 閉塞道路の情報を転記
    closed_info = closed_roads[closed_roads["路線ID"] == road_id]
    if not closed_info.empty:
        closed_info = closed_info.iloc[0]
        for field in ["int_area", "int_length", "max_width", "w_build_id", 
                      "is_closed", "c_build_id", "rem_area", "line_len", 
                      "car_access", "ped_access"]:
            attributes[field] = closed_info.get(field, None) if pd.notna(closed_info.get(field)) else None
    else:
        # 属性情報の初期化
        attributes.update({
            "int_area": 0,
            "int_length": 0,
            "max_width": 0,
            "w_build_id": None,
            "is_closed": False,
            "c_build_id": None,
            "rem_area": road_geom.area,
            "line_len": 0,
            "car_access": 1,
            "ped_access": 1,
        })

    split_geoms = [road_geom]

    # 倒壊建物との交差部分を削除
    for building in target_buildings.geometry:
        temp_split_geoms = []
        for geom in split_geoms:
            if geom.intersects(building):
                split_result = geom.difference(building)
                if isinstance(split_result, LineString):
                    temp_split_geoms.append(split_result)
                elif isinstance(split_result, MultiLineString):
                    temp_split_geoms.extend(split_result.geoms)
            else:
                temp_split_geoms.append(geom)
        split_geoms = temp_split_geoms

    # 該当するped_access=0のポリゴンと交差する場合、両端から1.2m短くする
    temp_geoms = []
    for geom in split_geoms:
        intersecting_roads = no_pedestrian_access_roads[no_pedestrian_access_roads.intersects(geom)]
        if not intersecting_roads.empty:
            try:
                road_length = geom.length
                if road_length > 2.4:  # 両端1.2mずつ短縮可能か確認
                    trimmed_geom = substring(geom, start_dist=1.2, end_dist=road_length - 1.2)
                    temp_geoms.append(trimmed_geom)
                else:
                    # 2.4m未満の場合は、最低0.5mを残す
                    trimmed_geom = substring(geom, start_dist=0.5, end_dist=road_length - 0.5)
                    temp_geoms.append(trimmed_geom)
            except Exception as e:
                print(f"Error trimming road {road_id}: {e}")
        else:
            temp_geoms.append(geom)
    split_geoms = temp_geoms

    # サフィックスを付加してエッジを作成
    if len(split_geoms) > 1:
        for i, segment in enumerate(split_geoms, 1):
            unique_road_id = f"{road_id}_{i:02d}"
            new_edge = attributes.copy()
            new_edge["路線ID"] = unique_road_id
            new_edge["geometry"] = segment
            new_edges.append(new_edge)
    else:
        new_edge = attributes.copy()
        new_edge["geometry"] = split_geoms[0]
        new_edges.append(new_edge)

# 必要な列を明示的に指定して新しいエッジデータフレームの作成
columns = list(attributes.keys())
new_edges_gdf = gpd.GeoDataFrame(new_edges, columns=columns, crs=roads.crs)

# データ型を変換（int64 -> int、ただし NaN がある場合は float）
for col in new_edges_gdf.columns:
    # int64 / Int64 系の列か確認
    if 'int' in str(new_edges_gdf[col].dtype):
        if new_edges_gdf[col].isna().any():
            # 欠損値がある場合は float に変換
            new_edges_gdf[col] = new_edges_gdf[col].astype(float)
        else:
            # 欠損値が無い場合だけ int 変換
            new_edges_gdf[col] = new_edges_gdf[col].astype(int)
    elif 'float' in str(new_edges_gdf[col].dtype):
        # float64 -> float へ(GeoPandas内部では同じfloatだが明示的に書く場合)
        new_edges_gdf[col] = new_edges_gdf[col].astype(float)


# 保存
new_edges_gdf.to_file(output_path, driver="GeoJSON", encoding="utf-8")
print(f"処理が完了しました。分割された道路中心線が保存されました: {output_path}")
