import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, LineString, MultiLineString, GeometryCollection

# ファイルパスの指定
road_path = r"C:\\szok\\import\\szoksrg_road_plateau_id.geojson"
building_path = r"C:\\szok\\szoksrg_simulation\\szoksrg_plateau_destruction.geojson"
output_path = r"C:\\szok\\szoksrg_simulation\\szoksrg_road_kosa_with_reductions.geojson"

# 道路と建物レイヤーの読み込み
roads = gpd.read_file(road_path, encoding="utf-8")
buildings = gpd.read_file(building_path, encoding="utf-8")
roads['道路幅'] = pd.to_numeric(roads['道路幅'], errors='coerce')

# 新しい属性列を追加
roads["int_area"] = 0.0     # 総交差面積
roads["int_length"] = 0.0   # 総交差長さ
roads["max_width"] = 0.0    # 最大幅員減少幅
roads["w_build_id"] = None  # 最大幅員減少を生じさせた建物ID
roads["is_closed"] = False  # 閉塞状態
roads["c_build_id"] = None  # 閉塞原因建物ID（複数の場合はセミコロン区切り）

# 閉塞判定の幅の閾値
MIN_WIDTH_THRESHOLD = 0.5              # 閉塞と判定する幅の閾値
CROSSING_SEGMENT_RATIO_THRESHOLD = 0.4 # 道路をまたぐかどうかを判定する比率（セグメントの長さの比率が0.4以上の場合、またぐと判定）

# 各道路ポリゴンに対して処理
for idx, road in roads.iterrows():
    max_reduction = 0.0
    is_closed = False
    road_width = road["道路幅"]
    road_boundary = road.geometry.boundary  # 道路の外周ライン
    building_ids = []  # 閉塞原因建物ID
    total_intersection_area = 0.0
    total_intersection_length = 0.0
    max_width_building_id = None

    # 各建物ポリゴンについて交差を確認
    for building_idx, building in buildings.iterrows():
        if road.geometry.intersects(building.geometry):
            # 交差面積
            intersection_area = road.geometry.intersection(building.geometry).area
            total_intersection_area += intersection_area

            # 境界線の交差長さ
            boundary_intersection = road_boundary.intersection(building.geometry)
            if isinstance(boundary_intersection, MultiLineString):
                boundary_length = max(segment.length for segment in boundary_intersection.geoms)
            elif isinstance(boundary_intersection, LineString):
                boundary_length = boundary_intersection.length
            elif isinstance(boundary_intersection, GeometryCollection):
                line_segments = [line for line in boundary_intersection.geoms if isinstance(line, LineString)]
                boundary_length = max((line.length for line in line_segments), default=0)
            else:
                boundary_length = 0

            total_intersection_length += boundary_length

            # 幅員減少幅
            if boundary_length > 0:
                width_reduction = intersection_area / boundary_length
                if road_width - width_reduction < MIN_WIDTH_THRESHOLD:
                    is_closed = True
                    building_ids.append(building['id'])
                elif width_reduction > max_reduction:
                    max_reduction = width_reduction
                    max_width_building_id = building['id']

    # 属性の更新
    roads.at[idx, "int_area"] = total_intersection_area
    roads.at[idx, "int_length"] = total_intersection_length
    roads.at[idx, "max_width"] = max_reduction
    roads.at[idx, "w_build_id"] = max_width_building_id
    roads.at[idx, "is_closed"] = is_closed
    roads.at[idx, "c_build_id"] = ";".join(map(str, building_ids)) if building_ids else None

# 保存
roads.to_file(output_path, driver="GeoJSON", encoding="utf-8")

print(f"処理が完了しました。結果は以下に保存されています: {output_path}")
