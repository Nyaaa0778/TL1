import bpy

import mathutils

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
    
class MYADDON_OT_add_collider(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_add_collider"
    bl_label = "コライダー 追加"
    bl_description = "['collider'] カスタムプロパティを追加します"
    # リドゥ / アンドゥ（Ctrl + Shift + Z / Ctrl + Z）可能オプション
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # ['collider']カスタムプロパティを追加（初期値は"BOX"）
        context.object["collider"] = "BOX"
        context.object["collider_center"] = mathutils.Vector((0, 0, 0))
        context.object["collider_size"] = mathutils.Vector((2, 2, 2))
        return {"FINISHED"}
    
classes = (
    MYADDON_OT_add_filename,
    MYADDON_OT_add_collider,
)