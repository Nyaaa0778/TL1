import bpy

import bpy_extras

import json

class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"

    # 出力するファイルの拡張子
    filename_ext = ".json"

    def write_and_print(self, file, text):
        """コンソールとファイルの両方に同時に出力するヘルパー関数"""

        print(text) # コンソールに出力
        file.write(text + '\n') # ファイルに出力（改行を自動挿入）

    def parse_scene_recursive(self, file, obj, level):
        """シーン解析用再帰関数"""

        # 階層に合わせてタブでインデント
        indent = ''
        for i in range(level):
            indent += "\t"

        # オブジェクトのタイプ名のみを出力
        self.write_and_print(file, indent + obj.type)
        
        # トランスフォーム分解
        trans, rot, scale = obj.matrix_local.decompose()

        # 回転を Quaternion からEuler（3軸での回転角）に変換
        rot = rot.to_euler()
        
        # --- 座標系変換（テキスト出力用） ---
        # Blender(X, Y, Z) -> Game(X, Z, Y) などの軸変換を行う
        # 回転はC++側で反転させていたので、ここでマイナスをかける
        trans_x, trans_y, trans_z = trans.x, trans.z, trans.y
        rot_x, rot_y, rot_z = -rot.x, -rot.z, -rot.y
        scale_x, scale_y, scale_z = scale.x, scale.z, scale.y
        
        # トランスフォーム情報をフォーマット（T, R, S）で表示
        self.write_and_print(file, indent + "T %f %f %f" % (trans_x, trans_y, trans_z))
        self.write_and_print(file, indent + "R %f %f %f" % (rot_x, rot_y, rot_z))
        self.write_and_print(file, indent + "S %f %f %f" % (scale_x, scale_y, scale_z))
        
        # カスタムプロパティ 'file_name' があれば "N パス" を出力
        if "file_name" in obj:
            self.write_and_print(file, indent + "N %s" % obj["file_name"])
            
        # カスタムプロパティ 'collision'
        if "collider" in obj:
            self.write_and_print(file, indent + "C %s" % obj["collider"])
            
            # 文字列の頭文字と、取得したいプロパティ名をセットにして回す
            self.write_and_print(file, indent + "CC %f %f %f" % tuple(obj["collider_center"]))
            self.write_and_print(file, indent + "CS %f %f %f" % tuple(obj["collider_size"]))

        # データの区切りとして 'END' と空行を出力
        self.write_and_print(file, indent + 'END')
        self.write_and_print(file, '')

        # 子オブジェクトも再帰的に処理する
        for child in obj.children:
            self.parse_scene_recursive(file, child, level + 1)

    def export(self, context):
        """書き出しのメイン処理"""

        print("シーン情報出力中... %r" % self.filepath)

        # ファイルをテキスト形式で書き出し用にオープン
        with open(self.filepath, "wt") as file:
            
            # ファイルに文字列を差し込む
            self.write_and_print(file, "SCENE")

            # シーン内の全オブジェクトを取得
            obj_list = list(context.scene.objects)

            # シーン直下のオブジェクトを走査
            for obj in obj_list:
                # 親オブジェクトがあるものはスキップ（親から再帰的に呼び出されるため）
                if obj.parent:
                    continue
                
                # 親がいないルートノード（深さ 0）として再帰関数をスタート
                self.parse_scene_recursive(file, obj, 0)

    def parse_scene_recursive_json(self, data_parent, object, level):
        # シーンのオブジェクト1個分のjsonオブジェクト生成
        json_object = dict()
        # オブジェクトの種類
        if "type" in object:
            json_object["type"] = object["type"]
        else:
            json_object["type"] = object.type
        # オブジェクト名
        json_object["name"] = object.name

        # オブジェクトのローカルトランスフォームから
        # 平行移動、回転、拡縮を抽出
        trans, rot, scale = object.matrix_local.decompose()
        # 回転を Quaternion から Euler（3軸での回転角）に変換
        rot = rot.to_euler()

        # --- 座標系変換（JSON出力用） ---
        # 自作エンジン(X:左右, Y:上下, Z:前後) に合わせて
        # Blender(X:左右, Y:前後, Z:上下) の Y と Z を入れ替える
        transform = {
            "translation": (trans.x, trans.z, trans.y),
            # ※回転の正負はエンジンの仕様（左手/右手座標系）に依存します。
            # もしエンジン内で回転が逆になる場合は、ここのマイナス符号を調整してください。
            "rotation": (-rot.x, -rot.z, -rot.y),
            "scaling": (scale.x, scale.z, scale.y)
        }

        # まとめて1個分のjsonオブジェクトに登録
        json_object["transform"] = transform

        # カスタムプロパティ 'file_name'
        if "file_name" in object:
            json_object["file_name"] = object["file_name"]

        # コライダーの座標系も変換
        if "collider" in object:
            c_center = object["collider_center"]
            c_size = object["collider_size"]
            
            json_object["collider"] = {
                "type": object["collider"],
                # X, Y, Z -> X, Z, Y に入れ替えて出力
                "center": (c_center[0], c_center[2], c_center[1]),
                "size": (c_size[0], c_size[2], c_size[1])
            }

        # 描画無効化オプション
        if "disabled" in object:
            json_object["disabled"] = bool(object["disabled"])

        # 1個分のjsonオブジェクトを親オブジェクトに登録
        data_parent.append(json_object)

        # 直接の子供リストを走査
        if len(object.children) > 0:
            # 子ノードリストを作成
            json_object["children"] = list()

            # 子ノードへ進む（深さが 1 上がる）
            for child in object.children:
                self.parse_scene_recursive_json(json_object["children"], child, level + 1)


    def export_json(self):
        """JSON形式でファイルに出力"""

        # 保存する情報をまとめるdict
        json_object_root = dict()

        # ノード名
        json_object_root["name"] = "scene"
        # オブジェクトリストを作成
        json_object_root["objects"] = list()

        # シーン内の全オブジェクト走査してパック
        for object in bpy.context.scene.objects:
            # 親オブジェクトがあるものはスキップ
            if(object.parent):
                continue

            # シーン直下のオブジェクトをルートモード（深さ 0）として再帰関数で走査
            self.parse_scene_recursive_json(json_object_root["objects"], object, 0)

        # オブジェクトをJSON文字列にエンコード
        json_text = json.dumps(json_object_root, ensure_ascii = False, cls = json.JSONEncoder, indent = 4)
        # コンソールに表示してみる
        print(json_text)

        # ファイルをテキスト形式で書き出し用にオープン
        # スコープを抜けると自動的にクローズされる
        with open(self.filepath, "wt", encoding = "utf-8") as file:
            # ファイルに文字列を書き込む
            file.write(json_text)

    def execute(self, context):
        print("シーン情報をExportします")

        # export関数を呼び出して実際の処理を行う
        #self.export(context)
        self.export_json()

        self.report({'INFO'}, "シーン情報をExportしました")
        print("シーン情報をExportしました")

        return {'FINISHED'}
    
classes = (
    MYADDON_OT_export_scene,
)