import bpy
import os

class MYADDON_OT_spawn_import_symbol(bpy.types.Operator):
    bl_idname = "myaddon.spawn_import_symbol"
    bl_label = "出現ポイントシンボルImport"
    bl_description = "出現ポイントのシンボルをImportします"

    # 【修正1】タイポを修正 (Prottype -> Prototype)
    prototype_object_name = "PrototypePlayerSpawn"
    object_name = "PlayerSpawn"

    def execute(self, context):
        # 重複ロード防止
        if bpy.data.objects.get(self.prototype_object_name) is not None:
            return {'CANCELLED'}
        
        addon_directory = os.path.dirname(__file__)
        relative_path = "player/player.obj"
        full_path = os.path.join(addon_directory, relative_path)

        # インポート前に選択状態をクリア
        bpy.ops.object.select_all(action='DESELECT')

        # オブジェクトをインポート
        bpy.ops.wm.obj_import(
            'EXEC_DEFAULT',
            filepath=full_path,
            display_type='THUMBNAIL',
            forward_axis='Z',
            up_axis='Y'
        )
        
        # 回転を適用
        bpy.ops.object.transform_apply(
            location=False,
            rotation=True,
            scale=False,
            properties=False,
            isolate_users=False
        )

        # 【修正2】インポートされた「全て」のオブジェクトを取得
        imported_objects = context.selected_objects
        
        if not imported_objects:
            return {'CANCELLED'}

        # メインのオブジェクトの名前とカスタムプロパティを設定
        active_obj = context.active_object or imported_objects[0]
        active_obj.name = self.prototype_object_name
        active_obj["type"] = self.object_name

        # 【修正3】読み込んだすべてのパーツをシーンから完全に隔離
        for obj in imported_objects:
            obj.use_fake_user = True # 勝手に消えないように保護
            
            # 所属している「すべての」コレクションから除外（Outlinerから完全に消す）
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
        
        return {'FINISHED'}
    
class MYADDON_OT_spawn_create_symbol(bpy.types.Operator):
    bl_idname = "myaddon.myaddon_ot_spawn_create_symbol"
    bl_label = "出現ポイントシンボルの作成"
    bl_description = "出現ポイントのシンボルを作成します"
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
    bl_label = "エネミー出現ポイントの作成"
    bl_description = "敵の出現ポイントを作成します"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 赤いマテリアルの取得または作成
        mat_name = "EnemySpawnMaterial"
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                # ベースカラーを赤（R:1.0, G:0.1, B:0.1, A:1.0）に設定
                principled.inputs[0].default_value = (1.0, 0.1, 0.1, 1.0)

        # 立方体の作成
        bpy.ops.mesh.primitive_cube_add(size=1.5)
        obj = context.active_object
        obj.name = "Enemy"
        obj["type"] = "PlayerSpawn"
        
        # マテリアルを適用
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

        # 出現時間を設定
        frames_per_segment = getattr(context.scene, "timeline_frames_per_segment", 100.0)
        if frames_per_segment <= 0.001:
            frames_per_segment = 100.0
        obj["spawn_time"] = context.scene.frame_current / frames_per_segment

        return {'FINISHED'}

classes = (
    MYADDON_OT_spawn_import_symbol,
    MYADDON_OT_spawn_create_symbol,
    MYADDON_OT_spawn_enemy_create_symbol,
)