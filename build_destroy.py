# モンテカルロ法で、全壊率に基づき建物の全壊シミュレーションを行う。建物高さ、階層から、周囲への影響範囲を指定して建物にバッファを発生させる。
import geopandas as gpd
import random

# ファイルパス
input_path = r"C:\szok\import\szoksrg_plateau_zenkairitsu.geojson"
output_path = r"C:\szok\szoksrg_simulation\szoksrg_plateau_destruction.geojson"

# データの読み込み
buildings = gpd.read_file(input_path)

# 無効なジオメトリを除外
buildings = buildings[~buildings.is_empty & buildings.is_valid]

# 倒壊結果列を初期化
buildings["倒壊結果"] = 0  # 0: 倒壊しない, 1: 倒壊

# モンテカルロシミュレーション
for idx, row in buildings.iterrows():
    zenkai1 = row["zenkai"]  # 全壊率
    tokaihani = row["tokaihani"]  # 倒壊影響範囲

    # 倒壊判定 (ランダムに全壊率を適用)
    if random.random() <= zenkai1:
        buildings.at[idx, "倒壊結果"] = 1
        try:
            # 倒壊範囲バッファを作成
            buildings.at[idx, "geometry"] = row["geometry"].buffer(tokaihani)
        except Exception as e:
            print(f"バッファ作成エラー (建物ID: {row['id']}): {e}")

# 出力ファイルに保存
buildings.to_file(output_path, driver="GeoJSON", encoding="utf-8")

print(f"倒壊建物ポリゴンが作成され、元データの属性情報とともに保存されました: {output_path}")
