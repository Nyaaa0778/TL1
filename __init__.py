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

# 各モジュールをインポート
from . import export_scene, mesh_tools, properties, ui, collider

# 各モジュール内で定義された classes タプルを展開して結合
classes = (
    *export_scene.classes,
    *mesh_tools.classes,
    *properties.classes,
    *ui.classes,
)

# Add-On有効化時コールバック
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # メニューに項目を追加
    bpy.types.TOPBAR_MT_editor_menus.append(ui.TOPBAR_MT_my_menu.submenu)
    
    # 3Dビューに描画関数を追加
    collider.DrawCollider.handle = bpy.types.SpaceView3D.draw_handler_add(
        collider.DrawCollider.draw_collider, (), "WINDOW", "POST_VIEW"
    )
    
    print("レベルエディタが有効化されました。")

# Add-On無効化時コールバック
def unregister():
    # メニューから項目を削除
    bpy.types.TOPBAR_MT_editor_menus.remove(ui.TOPBAR_MT_my_menu.submenu)

    # 3Dビューの描画関数を削除
    if collider.DrawCollider.handle:
        bpy.types.SpaceView3D.draw_handler_remove(collider.DrawCollider.handle, "WINDOW")
    
    # 登録した順番と逆に解除していく（エラー防止）
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("レベルエディタが無効化されました。")

if __name__ == "__main__":
    register()