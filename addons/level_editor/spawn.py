import bpy
import os

class MYADDON_OT_spawn_import_symbol(bpy.types.Operator):
    bl_idname = "myaddon.spawn_import_symbol"
    bl_label = "出現ポイントシンボルImport"
    bl_description = "出現ポイントのシンボルをImportします"

    prototype_object_name = "PrototypePlayerSpawn"
    object_name = "PlayerSpawn"

    def execute(self, context):
        if bpy.data.objects.get(self.prototype_object_name) is not None:
            return {'CANCELLED'}
        
        addon_directory = os.path.dirname(__file__)
        relative_path = "player/player.obj"
        full_path = os.path.join(addon_directory, relative_path)

        bpy.ops.object.select_all(action='DESELECT')

        bpy.ops.wm.obj_import(
            'EXEC_DEFAULT',
            filepath=full_path,
            display_type='THUMBNAIL',
            forward_axis='Z',
            up_axis='Y'
        )
        
        bpy.ops.object.transform_apply(
            location=False,
            rotation=True,
            scale=False,
            properties=False,
            isolate_users=False
        )

        imported_objects = context.selected_objects
        if not imported_objects:
            return {'CANCELLED'}

        active_obj = context.active_object or imported_objects[0]
        active_obj.name = self.prototype_object_name
        active_obj["type"] = self.object_name

        for obj in imported_objects:
            obj.use_fake_user = True
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
        
        return {'FINISHED'}
    
class MYADDON_OT_spawn_create_symbol(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_spawn_create_symbol"
    bl_label = "出現ポイントシンボルの作成"
    bl_description = "プレイヤー出現ポイントのシンボルを作成します"
    bl_options = {'REGISTER', 'UNDO'}

    object_name = "PlayerSpawn"

    def execute(self, context):
        spawn_object = bpy.data.objects.get(MYADDON_OT_spawn_import_symbol.prototype_object_name)

        if spawn_object is None:
            bpy.ops.myaddon.spawn_import_symbol('EXEC_DEFAULT')
            spawn_object = bpy.data.objects.get(MYADDON_OT_spawn_import_symbol.prototype_object_name)

        if spawn_object is None:
            self.report({'WARNING'}, "プロトタイプの読み込みに失敗しました")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')

        object = spawn_object.copy()
        bpy.context.collection.objects.link(object)
        object.name = self.object_name

        return {'FINISHED'}
    
class MYADDON_OT_spawn_enemy_create_symbol(bpy.types.Operator):
    bl_idname = "myaddon.spawn_enemy_create_symbol"
    bl_label = "突進エネミー出現ポイントの作成"
    bl_description = "突進エネミー(Rusher)の出現ポイントを作成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 赤色マテリアルの取得または作成
        mat_name = "EnemySpawnMaterial"
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                principled.inputs[0].default_value = (1.0, 0.1, 0.1, 1.0)

        bpy.ops.mesh.primitive_cube_add(size=1.5)
        obj = context.active_object
        obj.name = "Enemy_Rusher"
        obj["type"] = "PlayerSpawn"
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

        frames_per_segment = getattr(context.scene, "timeline_frames_per_segment", 100.0)
        if frames_per_segment <= 0.001:
            frames_per_segment = 100.0
        obj["spawn_time"] = context.scene.frame_current / frames_per_segment

        return {'FINISHED'}


class MYADDON_OT_spawn_formation_enemy_create_symbol(bpy.types.Operator):
    bl_idname = "myaddon.spawn_formation_enemy_create_symbol"
    bl_label = "編隊エネミー出現ポイントの作成"
    bl_description = "編隊飛行ドローンエネミー(Formation Drone)の出現ポイントを作成します"
    bl_options = {'REGISTER', 'UNDO'}

    pattern: bpy.props.EnumProperty(
        name="飛行パターン",
        items=[
            ('Wave', 'Wave (サイン波ウェーブ)', '上下左右に波打ちながら飛行する編隊'),
            ('Circle', 'Circle (円旋回)', '円を描いて旋回しながら前進する編隊'),
            ('Slalom', 'Slalom (スラローム蛇行)', '大きく左右にS字蛇行する編隊'),
            ('FigureEight', 'FigureEight (8の字旋回)', '8の字を描きながら飛行する編隊'),
        ],
        default='Wave'
    )

    def execute(self, context):
        # シアン色マテリアルの取得または作成
        mat_name = "FormationDroneSpawnMaterial"
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                # シアン/スカイブルー色 (R:0.1, G:0.8, B:1.0, A:1.0)
                principled.inputs[0].default_value = (0.1, 0.8, 1.0, 1.0)

        # ドローン用の小型シンボル（1.0サイズ）
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        obj = context.active_object
        obj.name = f"Enemy_Formation_{self.pattern}"
        obj["type"] = "PlayerSpawn"
        
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

        frames_per_segment = getattr(context.scene, "timeline_frames_per_segment", 100.0)
        if frames_per_segment <= 0.001:
            frames_per_segment = 100.0
        obj["spawn_time"] = context.scene.frame_current / frames_per_segment

        return {'FINISHED'}


classes = (
    MYADDON_OT_spawn_import_symbol,
    MYADDON_OT_spawn_create_symbol,
    MYADDON_OT_spawn_enemy_create_symbol,
    MYADDON_OT_spawn_formation_enemy_create_symbol,
)
