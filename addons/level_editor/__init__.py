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

import bpy
import json
import os
import socket
import blf

# 各モジュールをインポート
from . import export_scene, mesh_tools, properties, ui, collider, disabled, spawn, replay_debugger, import_scene, rail_drawer, timeline_editor

def register_handlers():
    replay_debugger.register_handlers()

def unregister_handlers():
    replay_debugger.unregister_handlers()

# 各モジュール内で定義された classes タプルを展開して結合
classes = (
    *export_scene.classes,
    *import_scene.classes,
    *mesh_tools.classes,
    *properties.classes,
    *ui.classes,
    *disabled.classes,
    *spawn.classes,
    *replay_debugger.classes,
    *timeline_editor.classes,
)


# 3Dビューの「追加 > メッシュ」メニューに追加する項目
def menu_func(self, context):
    self.layout.separator()
    self.layout.operator(spawn.MYADDON_OT_spawn_create_symbol.bl_idname, text="プレイヤー出現ポイント作成")
    self.layout.operator(spawn.MYADDON_OT_spawn_enemy_create_symbol.bl_idname, text="突進エネミー出現ポイント作成")
    self.layout.operator_menu_enum(
        spawn.MYADDON_OT_spawn_formation_enemy_create_symbol.bl_idname,
        "pattern",
        text="編隊エネミー出現ポイント作成 (Drone)..."
    )


# Add-On有効化時コールバック
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # タイムライン同期・ビューポート描画等のイベント登録
    register_handlers()
    timeline_editor.register()

    # メニューに項目を追加
    bpy.types.TOPBAR_MT_editor_menus.append(ui.TOPBAR_MT_my_menu.submenu)

    # 「追加 > メッシュ」メニューに項目を追加
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

    # 3Dビューに描画関数を追加
    collider.DrawCollider.handle = bpy.types.SpaceView3D.draw_handler_add(
        collider.DrawCollider.draw_collider, (), "WINDOW", "POST_VIEW"
    )
    rail_drawer.register_handlers()
    
    print("レベルエディタが有効化されました。")

# Add-On無効化時コールバック
def unregister():
    # タイムライン同期・ビューポート描画等のイベント登録解除
    unregister_handlers()
    timeline_editor.unregister()

    # 「追加 > メッシュ」から削除（エラー防止のため最初に実行）
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

    # メニューから項目を削除
    bpy.types.TOPBAR_MT_editor_menus.remove(ui.TOPBAR_MT_my_menu.submenu)

    # 3Dビューの描画関数を削除
    if collider.DrawCollider.handle:
        bpy.types.SpaceView3D.draw_handler_remove(collider.DrawCollider.handle, "WINDOW")
    rail_drawer.unregister_handlers()
    
    # 登録した順と逆に解除していく（エラー防止）
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("レベルエディタが無効化されました。")

if __name__ == "__main__":
    register()
