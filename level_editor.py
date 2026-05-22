import bpy

# 標準数学モジュール
import math

import bpy_extras

import gpu
import gpu_extras.batch

import copy

bl_info = {
    "name": "LevelEditor",
    "author": "Taro Kamata",
    "version": (1, 0),
    "blender": (3, 3, 1),
    "location": "",
    "description": "LevelEditor",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}

# =========================================================================
# オペレータ（実際の処理を定義するクラス群）
# =========================================================================

class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"

    # 出力するファイルの拡張子
    filename_ext = ".scene"

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

        # 1. オブジェクトのタイプ名のみを出力
        self.write_and_print(file, indent + obj.type)
        
        # トランスフォーム分解
        trans, rot, scale = obj.matrix_local.decompose()

        # 回転を Quaternion からEuler（3軸での回転角）に変換
        rot = rot.to_euler()
        # ラジアンから度数法に変換
        rot.x = math.degrees(rot.x)
        rot.y = math.degrees(rot.y)
        rot.z = math.degrees(rot.z)
        
        # 2. トランスフォーム情報をフォーマット（T, R, S）で表示
        self.write_and_print(file, indent + "T %f %f %f" % (trans.x, trans.y, trans.z))
        self.write_and_print(file, indent + "R %f %f %f" % (rot.x, rot.y, rot.z))
        self.write_and_print(file, indent + "S %f %f %f" % (scale.x, scale.y, scale.z))
        
        # 3. カスタムプロパティ 'file_name' があれば "N パス" を出力
        if "file_name" in obj:
            self.write_and_print(file, indent + "N %s" % obj["file_name"])
            
        # 4. データの区切りとして 'END' と空行を出力
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

    def execute(self, context):
        print("シーン情報をExportします")

        # export関数を呼び出して実際の処理を行う
        self.export(context)

        self.report({'INFO'}, "シーン情報をExportしました")
        print("シーン情報をExportしました")

        return {'FINISHED'}

class MYADDON_OT_stretch_vertex(bpy.types.Operator):
    """特定の頂点を伸ばすオペレータ"""

    bl_idname = "myaddon.myaddon_ot_stretch_vertex"
    bl_label = "頂点を伸ばす"
    bl_description = "頂点座標を引っ張って伸ばします"

    # リドゥ / アンドゥ（Ctrl + Shift + Z / Ctrl + Z）可能オプション
    bl_options = {'REGISTER', 'UNDO'}

    # メニューを実行したときに呼ばれるコールバック関数
    def execute(self, context):
        bpy.data.objects["Cube"].data.vertices[0].co.x += 1.0
        print("頂点を伸ばしました。")

        # オペレータの命令終了通知
        return {'FINISHED'}

class MYADDON_OT_create_ico_sphere(bpy.types.Operator):
    """ICO球を生成するオペレータ"""

    bl_idname = "myaddon.myaddon_ot_create_object"
    bl_label = "ICO球生成"
    bl_description = "ICO球を生成します"

    # リドゥ / アンドゥ（Ctrl + Shift + Z / Ctrl + Z）可能オプション
    bl_options = {'REGISTER', 'UNDO'}

    # メニューを実行したときに呼ばれる関数
    def execute(self, context):
        bpy.ops.mesh.primitive_ico_sphere_add()
        print("ICO球を生成しました。")

        # オペレータの命令終了通知
        return {'FINISHED'}

# =========================================================================
# UIメニュー（画面上部への表示設定）
# =========================================================================

class TOPBAR_MT_my_menu(bpy.types.Menu):
    """トップバーの拡張メニュー"""

    # Blenderがクラスを識別する為の固有の文字列
    bl_idname = "TOPBAR_MT_my_menu"
    # メニューのラベルとして表示される文字列
    bl_label = "MyMenu"
    # 著者表示用の文字列
    bl_description = "拡張メニュー by " + bl_info["author"]

    # サブメニューの描画
    def draw(self, context):
        # トップバーの「エディターメニュー」に項目（オペレータ）を追加

        # シーン情報を走査
        self.layout.operator(MYADDON_OT_export_scene.bl_idname,text=MYADDON_OT_export_scene.bl_label)
        
        # 区切り線
        self.layout.separator()

        # 頂点を伸ばす
        self.layout.operator(MYADDON_OT_stretch_vertex.bl_idname,
                             text=MYADDON_OT_stretch_vertex.bl_label)
        # 区切り線
        self.layout.separator()

        # ICO球を生成
        self.layout.operator(MYADDON_OT_create_ico_sphere.bl_idname,
                             text=MYADDON_OT_create_ico_sphere.bl_label)
        
        # self.layout.operator("wm.url_open_preset", text = "Manual", icon = 'HELP')
        # # 区切り線
        # self.layout.separator()
        # self.layout.operator("wm.url_open_preset", text = "Manual", icon = 'HELP')


    # 既存のメニューにサブメニューを追加
    def submenu(self, context):
        # 既存のメニューにサブメニューを追加するための関数
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

# =========================================================================
# カスタムプロパティ・パネル
# =========================================================================

class MYADDON_OT_add_filename(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_add_filename"
    bl_label = "FileName 追加"
    bl_description = "['file_name'] カスタムプロパティを追加します"
    # リドゥ / アンドゥ（Ctrl + Shift + Z / Ctrl + Z）可能オプション
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # ['file_name']カスタムプロパティを追加
        context.object["file_name"] = ""
        return {"FINISHED"}

class OBJECT_PT_file_name(bpy.types.Panel):
    """オブジェクトのファイルネームパネル"""

    bl_idname = "OBJECT_PT_file_name"
    bl_label = "FileName"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    # サブメニューの描画
    def draw(self, context):
        # パネルに項目を追加
        if "file_name" in context.object:
            # 既にプロパティがあればプロパティを表示
            self.layout.prop(context.object,'["file_name"]', text = self.bl_label)
        else:
            # プロパティがなければ、プロパティを追加ボタンを表示
            self.layout.operator(MYADDON_OT_add_filename.bl_idname)

# =========================================================================
# コライダー描画
# =========================================================================

class DrawCollider:
    # 描画ハンドル
    handle = None

    def draw_collider():
        """3Dビューに登録する描画関数"""
        
        # 3D空間描画用のシェーダを取得 
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")

        # 頂点データとインデックスデータ
        vertices = []
        indices = []

        # 各頂点のオブジェクトの中心からのオフセット
        offsets = [
            [-0.5, -0.5, -0.5], # 左下前
            [+0.5, -0.5, -0.5], # 右下前
            [-0.5, +0.5, -0.5], # 左上前
            [+0.5, +0.5, -0.5], # 右上前
            [-0.5, -0.5, +0.5], # 左下奥
            [+0.5, -0.5, +0.5], # 右下奥
            [-0.5, +0.5, +0.5], # 左上奥
            [+0.5, +0.5, +0.5], # 右上奥
        ]

        # 立方体のX, Y, Z方向サイズ
        size = [2, 2, 2]

        # 現在のシーンのオブジェクトリストを走査
        for object in bpy.context.scene.objects:
            # 追加前の頂点数
            start = len(vertices)

            # Boxの8頂点分回す
            for offset in offsets:
                # オブジェクトの中心座標をコピー
                pos = copy.copy(object.location)
                # 中心座標を基準に拡張店ごとにずらす
                pos[0] += offset[0] * size[0]
                pos[1] += offset[1] * size[1]
                pos[2] += offset[2] * size[2]

                # 頂点データリストに座標を追加
                vertices.append(pos)

            # 前面を構成する辺の頂点インデックス
            indices.append([start + 0, start + 1])
            indices.append([start + 2, start + 3])
            indices.append([start + 0, start + 2])
            indices.append([start + 1, start + 3])

            # 奥面を構成する辺の頂点インデックス
            indices.append([start + 4, start + 5])
            indices.append([start + 6, start + 7])
            indices.append([start + 4, start + 6])
            indices.append([start + 5, start + 7])

            # 手面を構成する辺の頂点インデックス
            indices.append([start + 0, start + 4])
            indices.append([start + 1, start + 5])
            indices.append([start + 2, start + 6])
            indices.append([start + 3, start + 7])

        if not vertices:
            return

        # 頂点フォーマット（GPUVertexFormat）を明示的に作成
        # "pos" という名前に、3次元(3)の浮動小数点("F32")が入ることを教える
        fmt = gpu.types.GPUVertFormat()
        fmt.attr_add(id="pos", comp_type="F32", len=3, fetch_mode="FLOAT")

        # フォーマットに沿ってVBO（頂点バッファオブジェクト）を作成
        vbo = gpu.types.GPUVertBuf(len=len(vertices), format=fmt)
        vbo.attr_fill(id="pos", data=vertices)

        # インデックスバッファ（IBO）を作成
        ibo = gpu.types.GPUIndexBuf(type="LINES", seq=indices)

        # シェーダ、VBO、IBOを組み合わせてバッチを作成
        batch = gpu.types.GPUBatch(type="LINES", buf=vbo, elem=ibo)

        # バインドして描画
        shader.bind()
        
        # 色の設定 (R, G, B, A)
        color = [0.5, 1.0, 1.0, 1.0]
        shader.uniform_float("color", color)
        
        batch.draw(shader)

# =========================================================================
# 登録・解除（Blender起動・終了時の処理）
# =========================================================================

# Blenderに登録するクラスリスト
classes = (
    MYADDON_OT_export_scene,
    MYADDON_OT_stretch_vertex,
    MYADDON_OT_create_ico_sphere,
    TOPBAR_MT_my_menu,
    MYADDON_OT_add_filename,
    OBJECT_PT_file_name
)

# Add-On有効化時コールバック
def register():
    # Blenderにクラスを登録
    for cls in classes:
        bpy.utils.register_class(cls)

    # メニューに項目を追加（スライドの変更指示部分）
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_my_menu.submenu)
    
    # 3Dビューに描画関数を追加
    DrawCollider.handle = bpy.types.SpaceView3D.draw_handler_add(DrawCollider.draw_collider, (), "WINDOW", "POST_VIEW")
    
    print("レベルエディタが有効化されました。")

# Add-On無効化時コールバック
def unregister():
    # メニューから項目を削除（スライドの変更指示部分）
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_my_menu.submenu)

    # 3Dビューに描画関数を削除
    bpy.types.SpaceView3D.draw_handler_remove(DrawCollider.handle, "WINDOW")
    

    # Blenderからクラスを削除
    for cls in classes:
        bpy.utils.unregister_class(cls)

    print("レベルエディタが無効化されました。")

if __name__ == "__main__":
    register()