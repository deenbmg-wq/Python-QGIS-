import os
import shutil
import pandas as pd
import geopandas as gpd
import time

# 各スクリプトのパス
scripts = [
    r"C:\\szok\\sim01\\build_destroy.py",
    r"C:\\szok\\sim01\\wait.py",
    r"C:\\szok\\sim01\\cross_analysis7.py",
    r"C:\\szok\\sim01\\wait.py",
    r"C:\\szok\\sim01\\area_analysis.py",
    r"C:\\szok\\sim01\\wait.py",
    r"C:\\szok\\sim01\\closedpoint2.py",
    r"C:\\szok\\sim01\\wait.py",
    r"C:\\szok\\sim01\\node_edge3.py",
    r"C:\\szok\\sim01\\wait.py",
    r"C:\\szok\\sim01\\NetworkX7.py",
    r"C:\\szok\\sim01\\wait.py"
]

# 初期化
iteration_counter = 0  # 初期値を0に設定

# 繰り返し回数
iterations = 100

# 各フォルダのパス
temp_dir = r"C:\\szok\\simu01\\temp"
simulation_dir = r"C:\\szok\\simu01\\01_szok_simulation"
csv_output_dir = r"C:\\szok\\simu01\\01_szok_実行結果CSV"

os.makedirs(temp_dir, exist_ok=True)
os.makedirs(csv_output_dir, exist_ok=True)

# 出力ファイルのパス
output_files = {
    "szok_plateau_destruction.geojson": r"C:\\szok\\simu01\\01_szok_simulation\\szok_plateau_destruction.geojson",
    "szok_road_kosa_with_reductions.geojson": r"C:\\szok\\simu01\\01_szok_simulation\\szok_road_kosa_with_reductions.geojson",
    "szok_road_plateau_area_analysis.geojson": r"C:\\szok\\simu01\\01_szok_simulation\\szok_road_plateau_area_analysis.geojson",
    "szok_road_split_with_all_attributes.geojson": r"C:\\szok\\simu01\\01_szok_simulation\\szok_road_split_with_all_attributes.geojson",
    "szok_nodes.shp": r"C:\\szok\\simu01\\01_szok_simulation\\szok_nodes.shp",
    "szok_edges.shp": r"C:\\szok\\simu01\\01_szok_simulation\\szok_edges.shp",
    "szok_routes.shp": r"C:\\szok\\simu01\\01_szok_simulation\\szok_routes.shp",
}

# CSV 出力設定
csv_outputs = {
    "01_倒壊結果.csv": ["karo_plateau_destruction.geojson", ["id", "倒壊結果"]],
    "02_閉塞状況(max_width).csv": ["karo_road_plateau_area_analysis.geojson", ["路線ID", "max_width"]],
    "03_閉塞状況(w_build_id).csv": ["karo_road_plateau_area_analysis.geojson", ["路線ID", "w_build_id"]],
    "04_閉塞状況(is_closed).csv": ["karo_road_plateau_area_analysis.geojson", ["路線ID", "is_closed"]],
    "05_閉塞状況(c_build_id).csv": ["karo_road_plateau_area_analysis.geojson", ["路線ID", "c_build_id"]],
    "06_閉塞状況(car_access).csv": ["karo_road_plateau_area_analysis.geojson", ["路線ID", "car_access"]],
    "07_閉塞状況(ped_access).csv": ["karo_road_plateau_area_analysis.geojson", ["路線ID", "ped_access"]],
    "08_避難路検索結果(r_found).csv": ["karo_routes.shp", ["b_id", "r_found"]],
    "09_避難路検索結果(p_nodes).csv": ["karo_routes.shp", ["b_id", "p_nodes"]],
    "10_避難路検索結果(walk_f).csv": ["karo_routes.shp", ["b_id", "walk_f"]],
    "11_避難路検索結果(t_time).csv": ["karo_routes.shp", ["b_id", "t_time"]],
    "12_避難路検索結果(t_dist).csv": ["karo_routes.shp", ["b_id", "t_dist"]]
}

def copy_files_to_temp():
    """kから始まる成果物ファイルをTempにコピー"""
    for file_key, path in output_files.items():
        if not path or not os.path.exists(path):
            continue

        filename = os.path.basename(path)
        # "k"で始まるかチェック
        if filename.lower().startswith("k"):
            # 拡張子を取得
            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            try:
                if ext == ".shp":
                    # シェープファイルのコピー (.shp, .shx, .dbf, .prj, .cpg)
                    base = path[:-4]  # ".shp" を除いた部分
                    for add_ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                        shp_part = base + add_ext
                        if os.path.exists(shp_part):
                            shutil.copy(shp_part, temp_dir)
                elif ext == ".geojson":
                    # GeoJSONは単一ファイルをコピー
                    shutil.copy(path, temp_dir)

            except Exception as e:
                print(f"Error copying {path}: {e}")

def rename_files_in_temp(iteration):
    """Tempフォルダ内の"k"から始まるファイルをリネーム"""
    failed_renames = []  # リネームに失敗したファイルを記録するリスト
    for file_name in os.listdir(temp_dir):
        if file_name.lower().startswith("k"):  # 大文字・小文字を無視
            original_path = os.path.join(temp_dir, file_name)
            base, ext = os.path.splitext(file_name)
            renamed = f"{str(iteration).zfill(4)}_{file_name}"
            renamed_path = os.path.join(temp_dir, renamed)
            try:
                shutil.move(original_path, renamed_path)
                # print(f"Renamed: {file_name} -> {renamed}")
            except Exception as e:
                print(f"Error renaming {file_name}: {e}")
                failed_renames.append(file_name)
    
    # 失敗したファイルをログに出力
    if failed_renames:
        print(f"Failed to rename the following files: {failed_renames}")


def move_files_to_simulation():
    """Tempフォルダ内のファイルをSimulationフォルダに移動"""
    for file_name in os.listdir(temp_dir):
        try:
            shutil.move(os.path.join(temp_dir, file_name), simulation_dir)
        except Exception as e:
            print(f"Error moving {file_name}: {e}")

# 修正されたCSV出力関数
def extract_to_csv(temp_path, columns, output_csv, iteration):
    """Temp内のファイルを使ってCSVを作成・更新"""
    try:
        # まず拡張子判定
        _, ext = os.path.splitext(temp_path)
        ext = ext.lower()
        
        if ext not in [".geojson", ".shp"]:
            raise ValueError(f"Unsupported file format for {temp_path}. Only .geojson or .shp is supported.")
        # GeoDataFrame 読み込み
        gdf = gpd.read_file(temp_path, encoding="utf-8")

        # 路線IDが含まれる場合のみnotna()を適用
        if "路線ID" in columns:
            gdf = gdf[gdf["路線ID"].notna()]

        # 必要な列を選択
        selected = gdf[columns]

        # 初回のCSV作成
        if iteration == 1 or not os.path.exists(output_csv):
            selected.columns = [columns[0]] + [str(iteration) if col != columns[0] else col for col in columns[1:]]
            selected.to_csv(output_csv, index=False, encoding="utf-8")
            # print(f"CSV file created: {output_csv}")
        else:
            # 既存のCSVファイルに新しい列を追加
            existing = pd.read_csv(output_csv, encoding="utf-8")
            new_data = selected.rename(columns={columns[1]: str(iteration)})
            merged = pd.merge(existing, new_data, on=columns[0], how="left")
            merged.to_csv(output_csv, index=False, encoding="utf-8")
            print(f"CSV file updated: {output_csv}")

    except ValueError as ve:
        print(f"ValueError: {ve}")
    except FileNotFoundError:
        print(f"Temp file not found: {temp_path}")
    except KeyError as e:
        print(f"KeyError during CSV extraction: {e}")
    except Exception as e:
        print(f"Error extracting to CSV for {temp_path}: {e}")

# メイン処理
while iteration_counter < iterations:
    iteration_counter += 1  # カウンターをインクリメント
    print(f"=== Iteration {iteration_counter} started ===")

    # 各スクリプトを順次実行
    for script in scripts:
        try:
            print(f"Executing: {script}")
            exec(open(script, encoding="utf-8").read())
        except Exception as e:
            print(f"Error occurred while executing {script}: {e}")

    # Tempフォルダをクリア
    #for file in os.listdir(temp_dir):
    #    try:
    #        os.remove(os.path.join(temp_dir, file))
    #    except Exception as e:
    #        print(f"Error clearing Temp folder: {e}")

    # 成果物をTempフォルダにコピー
    copy_files_to_temp()

    # CSVファイルを作成・更新
    print(f"Extracting data to CSV for iteration {iteration_counter}...")
    for csv_name, (file_key, cols) in csv_outputs.items():
        temp_file_path = os.path.join(temp_dir, os.path.basename(output_files[file_key]))
        if os.path.exists(temp_file_path):
            extract_to_csv(temp_file_path, cols, os.path.join(csv_output_dir, csv_name), iteration_counter)

    # Tempフォルダ内でファイルをリネーム
    rename_files_in_temp(iteration_counter)

    # TempフォルダからSimulationフォルダに移動
    move_files_to_simulation()

    print(f"=== Iteration {iteration_counter} completed ===")
