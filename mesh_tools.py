import bpy

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
    
classes = (
    MYADDON_OT_stretch_vertex,
    MYADDON_OT_create_ico_sphere,
)