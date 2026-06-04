import bpy

class MYADDON_OT_add_disabled(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_add_disabled"
    bl_label = "無効オプション 追加"
    bl_description = "['disabled'] カスタムプロパティを追加します"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # bool型のカスタムプロパティを追加（画像1通り初期値はTrue）
        context.object["disabled"] = True
        return {"FINISHED"}

class OBJECT_PT_disabled(bpy.types.Panel):
    bl_idname = "OBJECT_PT_disabled"
    bl_label = "無効オプション"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        # カスタムプロパティ 'disabled' があればパネルにチェックボックスとして表示
        if "disabled" in context.object:
            self.layout.prop(context.object, '["disabled"]', text=self.bl_label)
        # なければカスタムプロパティ追加用のボタンを表示
        else:
            self.layout.operator("myaddon.myaddon_ot_add_disabled")

# __init__.py で一括登録するためのクラス群
classes = (
    MYADDON_OT_add_disabled,
    OBJECT_PT_disabled,
)