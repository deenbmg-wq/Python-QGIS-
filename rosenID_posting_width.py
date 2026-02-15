# rosenID_posting_width.py
# ------------------------------------------------------------
# 1) 道路ポリゴンごとに :
#    - 交差する中心線が 1 本だけ → その線の内部長を使って
#      幅員 = 面積 / 中心線長 を計算し、「路線ID」と「道路幅」を付与
#    - 交差する中心線が 2 本以上 → 交差点ポリゴンとみなし、
#      「交差点ID」のみ付与（幅員は計算しない）
#
# 2) 道路ラインごとに :
#    - 関連する道路ポリゴンの幅員の長さ加重平均をとり、「道路幅」を付与
# ------------------------------------------------------------

import geopandas as gpd
from collections import defaultdict

# ---------- ファイルパス ----------
road_line_path    = r"C:\shizuoka_plateau\szok_road\szoksrg_road_line.shp"              # 道路ライン
road_polygon_path = r"C:\shizuoka_plateau\szok_road\szoksrg_road_plateau.shp"   # 道路ポリゴン

out_polygon_path  = r"C:\shizuoka_plateau\szok_road\szoksrg_road_plateau_id.shp"
out_line_path     = r"C:\shizuoka_plateau\szok_road\szok_road_width.shp"

# ---------- 読み込み ----------
road_lines    = gpd.read_file(road_line_path)
road_polygons = gpd.read_file(road_polygon_path)

# 距離・面積計算のため、両方とも同じ「メートル単位の投影座標系」に揃えておく
# すでに平面直角系のはずですが、念のため
road_lines    = road_lines.to_crs(6676)      # 静岡なら JGD2011 / 平面直角 IX などに合わせる
road_polygons = road_polygons.to_crs(6676)

# ---------- 出力用列の準備 ----------
for col in ["路線ID", "道路幅", "交差点ID"]:
    if col not in road_polygons.columns:
        road_polygons[col] = None

if "道路幅" not in road_lines.columns:
    road_lines["道路幅"] = None

# 交差点ID 用カウンタ
intersection_id_counter = 1

# ライン側に幅を集約するための器（長さ加重平均用）
sum_len_by_line   = defaultdict(float)   # 各ラインに対応する「ポリゴン内の線分長」の合計
sum_wlen_by_line  = defaultdict(float)   # 幅×線分長 の合計

# ---------- メインループ：ポリゴンごと ----------
for idx, poly_row in road_polygons.iterrows():
    poly_geom = poly_row.geometry

    # このポリゴンと交差する中心線を取得
    intersecting = road_lines[road_lines.intersects(poly_geom)]

    if len(intersecting) == 0:
        # 何も交差しない → 幅・路線ID とも付与しない
        continue

    elif len(intersecting) == 1:
        # 単一の中心線とだけ交差 → 通常の道路ポリゴン
        line_row = intersecting.iloc[0]
        line_idx = line_row.name      # line の index
        line_geom = line_row.geometry

        # ポリゴン内部にある中心線の長さを計算
        seg_geom = line_geom.intersection(poly_geom)
        seg_len = seg_geom.length

        if seg_len <= 0:
            # ゼロ長なら幅員は計算しない
            continue

        area = poly_geom.area
        width = area / seg_len        # 幅員[m] = 面積 / 線分長

        # ポリゴン側に路線IDと幅員を付与
        road_polygons.at[idx, "路線ID"] = line_row.get("路線ID")
        road_polygons.at[idx, "道路幅"] = float(width)

        # ライン側の集約用に記録（長さ加重平均）
        sum_len_by_line[line_idx]  += seg_len
        sum_wlen_by_line[line_idx] += width * seg_len

    else:
        # 2 本以上の中心線と交差 → 交差点ポリゴンとみなす
        road_polygons.at[idx, "交差点ID"] = f"INTERSECTION_{intersection_id_counter:05d}"
        intersection_id_counter += 1
        # 幅員は付与しない（None のまま）

# ---------- ライン側に「道路幅」を反映 ----------
for line_idx, total_len in sum_len_by_line.items():
    if total_len <= 0:
        continue
    width = sum_wlen_by_line[line_idx] / total_len   # 長さ加重平均
    road_lines.at[line_idx, "道路幅"] = float(width)

# ---------- 保存 ----------
# ※ shapefile の文字コードは QGIS 側でUTF-8を指定して読むのが無難です
road_polygons.to_file(out_polygon_path)
road_lines.to_file(out_line_path)

print("処理完了")
print(f"  ポリゴン出力: {out_polygon_path}")
print(f"  ライン出力  : {out_line_path}")
# ------------------------------------------------------------
