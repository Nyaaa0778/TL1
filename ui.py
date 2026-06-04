import bpy

class TOPBAR_MT_my_menu(bpy.types.Menu):
    bl_idname = "TOPBAR_MT_my_menu"
    bl_label = "MyMenu"
    bl_description = "拡張メニュー by Taro Kamata" # bl_infoの参照を避け、文字列で直接指定

    def draw(self, context):
        # 相互インポートを防ぐため、bl_idnameを文字列で直接指定
        self.layout.operator("myaddon.myaddon_ot_export_scene", text="シーン出力")
        self.layout.separator()
        self.layout.operator("myaddon.myaddon_ot_stretch_vertex", text="頂点を伸ばす")
        self.layout.separator()
        self.layout.operator("myaddon.myaddon_ot_create_object", text="ICO球生成")

    def submenu(self, context):
        self.layout.menu(TOPBAR_MT_my_menu.bl_idname)

class OBJECT_PT_file_name(bpy.types.Panel):
    bl_idname = "OBJECT_PT_file_name"
    bl_label = "FileName"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        if "file_name" in context.object:
            self.layout.prop(context.object,'["file_name"]', text = self.bl_label)
        else:
            self.layout.operator("myaddon.myaddon_ot_add_filename")

class OBJECT_PT_collider(bpy.types.Panel):
    bl_idname = "OBJECT_PT_collider"
    bl_label = "Collider"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        if "collider" in context.object:
            self.layout.prop(context.object,'["collider"]', text = self.bl_label)
            self.layout.prop(context.object,'["collider_center"]', text = "Center")
            self.layout.prop(context.object,'["collider_size"]', text = "Size")
        else:
            self.layout.operator("myaddon.myaddon_ot_add_collider")

classes = (
    TOPBAR_MT_my_menu,
    OBJECT_PT_file_name,
    OBJECT_PT_collider,
)