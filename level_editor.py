import bpy

# 標準数学モジュール
import math

import bpy_extras

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

# オペレータ シーン出力
class MYADDON_OT_export_scene(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
    bl_idname = "myaddon.myaddon_ot_export_scene"
    bl_label = "シーン出力"
    bl_description = "シーン情報をExportします"

    # 出力するファイルの拡張子
    filename_ext = ".scene"

    def write_and_print(self, file, text):
        print(text) # コンソールに出力
        file.write(text) # ファイルに出力
        file.write('\n') # 改行を自動挿入

    def parse_scene_recursive(self, file, obj, level):
        """シーン解析用再帰関数"""

        indent = ''
        for i in range(level):
            indent += "\t"

        # オブジェクト名を書き込み
        self.write_and_print(file, indent + f"[{level}] {obj.type} - {obj.name}")
        trans, rot, scale = obj.matrix_local.decompose()
        # 回転を Quaternion からEuler（3軸での回転角）に変換
        rot = rot.to_euler()
        # ラジアンから度数法に変換
        rot.x = math.degrees(rot.x)
        rot.y = math.degrees(rot.y)
        rot.z = math.degrees(rot.z)
        
        # トランスフォーム情報を表示
        self.write_and_print(file,  indent + "Trans(%f, %f, %f)" % (trans.x,trans.y,trans.z))
        self.write_and_print(file,  indent + "Rot(%f, %f, %f)" % (rot.x,rot.y,rot.z))
        self.write_and_print(file,  indent + "Scale(%f, %f, %f)" % (scale.x,scale.y,scale.z))
        # 空行
        self.write_and_print(file, '')

        # 子オブジェクトも再帰的に処理する
        for child in obj.children:
            self.parse_scene_recursive(file, child, level + 1)

    def export(self, context):
        """ファイルに出力"""
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

# オペレータ 頂点を伸ばす
class MYADDON_OT_stretch_vertex(bpy.types.Operator):
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

# オペレータ ICO球生成
class MYADDON_OT_create_ico_sphere(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_create_object"
    bl_label = "ICO球生成"
    bl_description = "ICO球を生成します"

    # リドゥ / アンドゥ（Ctrl + Shift + Z / Ctrl + Z）可能オプション
    bl_option = {'REGISTER', 'UNDO'}

    # メニューを実行したときに呼ばれる関数
    def execute(self, context):
        bpy.ops.mesh.primitive_ico_sphere_add()
        print("ICO球を生成しました。")

        # オペレータの命令終了通知
        return {'FINISHED'}

# トップバーの拡張メニュー
class TOPBAR_MT_my_menu(bpy.types.Menu):
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
        # ID指定でサブメニューを追加
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

# Blenderに登録するクラスリスト
classes = (
    MYADDON_OT_export_scene,
    MYADDON_OT_stretch_vertex,
    MYADDON_OT_create_ico_sphere,
    TOPBAR_MT_my_menu,
)

# Add-On有効化時コールバック
def register():
    # Blenderにクラスを登録
    for cls in classes:
        bpy.utils.register_class(cls)

    # メニューに項目を追加（スライドの変更指示部分）
    bpy.types.TOPBAR_MT_editor_menus.append(TOPBAR_MT_my_menu.submenu)
    
    print("レベルエディタが有効化されました。")

# Add-On無効化時コールバック
def unregister():
    # メニューから項目を削除（スライドの変更指示部分）
    bpy.types.TOPBAR_MT_editor_menus.remove(TOPBAR_MT_my_menu.submenu)

    # Blenderからクラスを削除
    for cls in classes:
        bpy.utils.unregister_class(cls)

    print("レベルエディタが無効化されました。")

if __name__ == "__main__":
    register()