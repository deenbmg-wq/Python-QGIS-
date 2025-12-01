# 複数建物の全壊による道路ポリゴンの残存面積と車で走行、徒歩で走行に必要な面積を比較し閉塞判定を行う。
import geopandas as gpd
from shapely.geometry import LineString, MultiLineString

# ファイルパスの指定
road_polygon_path = r"C:\szok\szoksrg_simulation\szoksrg_road_kosa_with_reductions.geojson"
road_line_path = r"C:\szok\import\szoksrg_road.shp"
building_path = r"C:\szok\szoksrg_simulation\szoksrg_plateau_destruction.geojson"

# 車と徒歩の通行に必要な面積（m²）
CAR_PASSAGE_THRESHOLD = 1.5  # 車が通るために必要な幅（m）
PEDESTRIAN_PASSAGE_THRESHOLD = 0.5  # 人が通るために必要な幅（m）

# データの読み込み
road_polygons = gpd.read_file(road_polygon_path, encoding="utf-8")
road_lines = gpd.read_file(road_line_path, encoding="utf-8")
buildings = gpd.read_file(building_path, encoding="utf-8")

# 道路ポリゴンに新しい属性列を追加
road_polygons["rem_area"] = 0.0  # 残存面積
road_polygons["line_len"] = 0.0     # ラインの総長さ
road_polygons["car_access"] = True     # 車の通行可否
road_polygons["ped_access"] = True  # 人の通行可否

# 各道路ポリゴンについて処理
for idx, road_polygon in road_polygons.iterrows():
    total_intersection_area = 0.0

    # 倒壊建物との交差を確認
    for _, building in buildings.iterrows():
        if road_polygon.geometry.intersects(building.geometry):
            intersection = road_polygon.geometry.intersection(building.geometry)
            intersection_area = intersection.area
            total_intersection_area += intersection_area

    # 残存面積を計算
    remaining_area = road_polygon.geometry.area - total_intersection_area
    road_polygons.at[idx, "rem_area"] = remaining_area

    # 道路ラインとの交差を計算
    intersecting_lines = road_lines[road_lines.intersects(road_polygon.geometry)]
    total_line_length = 0.0
    for _, line in intersecting_lines.iterrows():
        intersection = road_polygon.geometry.intersection(line.geometry)
        if not intersection.is_empty and isinstance(intersection, (LineString, MultiLineString)):
            total_line_length += intersection.length
    road_polygons.at[idx, "line_len"] = total_line_length

    # 通行可否を判定
    car_threshold_area = CAR_PASSAGE_THRESHOLD * total_line_length
    pedestrian_threshold_area = PEDESTRIAN_PASSAGE_THRESHOLD * total_line_length

    road_polygons.at[idx, "car_access"] = remaining_area >= car_threshold_area
    road_polygons.at[idx, "ped_access"] = remaining_area >= pedestrian_threshold_area

# 結果を保存
output_path = r"C:\szok\szoksrg_simulation\szoksrg_road_plateau_area_analysis.geojson"
road_polygons.to_file(output_path, driver="GeoJSON", encoding="utf-8")

print(f"処理が完了しました。結果は以下に保存されています: {output_path}")
