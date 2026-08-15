import bpy
import bpy_extras
import json
import os
import mathutils

class MYADDON_OT_import_scene(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "myaddon.myaddon_ot_import_scene"
    bl_label = "シーン読込"
    bl_description = "JSONからシーンとレール情報を読み込みます"

    filename_ext = ".json"

    def clear_scene_objects(self):
        # 既存の編集用オブジェクト（カスタムプロパティを持つか、名前がRailのもの）を削除
        # ただし、PrototypePlayerSpawn などの保護オブジェクトは削除しない
        objs_to_remove = []
        for obj in bpy.data.objects:
            if obj.name == "PrototypePlayerSpawn":
                continue
            if obj.name == "Rail" or "file_name" in obj or "collider" in obj or "type" in obj:
                objs_to_remove.append(obj)
        
        # 削除実行
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objs_to_remove:
            obj.select_set(True)
        bpy.ops.object.delete()

    def create_mesh_object(self, name, file_name):
        import bmesh
        
        mesh = bpy.data.meshes.new(name=f"{name}_Mesh")
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        if file_name == "sphere":
            bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        else:
            bmesh.ops.create_cube(bm, size=2.0)
            
        bm.to_mesh(mesh)
        bm.free()
        
        obj["file_name"] = file_name
        return obj

    def create_spawn_object(self, name, entity_type):
        import bmesh
        
        # "Enemy" が名前に含まれるか、entity_type が Enemy なら敵、それ以外はPlayerSpawn
        if "Enemy" in name or entity_type == "Enemy":
            # 赤いマテリアルの取得または作成
            mat_name = "EnemySpawnMaterial"
            mat = bpy.data.materials.get(mat_name)
            if mat is None:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
                principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if principled:
                    principled.inputs[0].default_value = (1.0, 0.1, 0.1, 1.0)
            
            # メッシュとオブジェクトを作成 (API経由)
            mesh = bpy.data.meshes.new(name="EnemyMesh")
            obj = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(obj)
            
            # 立方体形状を生成 (サイズ 1.5)
            bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1.5)
            bm.to_mesh(mesh)
            bm.free()
            
            # マテリアルを適用
            obj.data.materials.append(mat)
            obj["type"] = "PlayerSpawn"
        else:
            # プレイヤー出現ポイント
            # まずプロトタイプが存在するか確認
            spawn_proto = bpy.data.objects.get("PrototypePlayerSpawn")
            if not spawn_proto:
                # 存在しない場合のみ、オペレータを呼び出してインポートを試みる
                try:
                    bpy.ops.myaddon.spawn_import_symbol('EXEC_DEFAULT')
                    spawn_proto = bpy.data.objects.get("PrototypePlayerSpawn")
                except Exception as e:
                    print(f"Failed to import PrototypePlayerSpawn via operator: {e}")
            
            if spawn_proto:
                obj = spawn_proto.copy()
                bpy.context.collection.objects.link(obj)
                obj.name = name
            else:
                # フォールバックとして緑の立方体を配置する
                mesh = bpy.data.meshes.new(name="PlayerSpawnMesh")
                obj = bpy.data.objects.new(name, mesh)
                bpy.context.collection.objects.link(obj)
                bm = bmesh.new()
                bmesh.ops.create_cube(bm, size=1.5)
                bm.to_mesh(mesh)
                bm.free()
                obj["type"] = "PlayerSpawn"
                
        return obj

    def apply_transform(self, obj, transform_data):
        # 位置 (ゲーム: X, Y, Z -> Blender: X, Z, Y)
        tx, ty, tz = transform_data.get("translation", (0.0, 0.0, 0.0))
        obj.location = (tx, tz, ty)
        
        # スケール (ゲーム: X, Y, Z -> Blender: X, Z, Y)
        sx, sy, sz = transform_data.get("scaling", (1.0, 1.0, 1.0))
        obj.scale = (sx, sz, sy)
        
        # 回転 (ゲーム: X, Y, Z -> Blender: X, Z, Y、かつマイナス反転)
        rx, ry, rz = transform_data.get("rotation", (0.0, 0.0, 0.0))
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (-rx, -rz, -ry)

    def import_object_recursive(self, data_obj, parent_obj=None):
        name = data_obj.get("name", "Object")
        obj_type = data_obj.get("type", "MESH")
        
        obj = None
        if obj_type == "PlayerSpawn":
            entity_type = data_obj.get("entity_type", "PlayerSpawn")
            obj = self.create_spawn_object(name, entity_type)
        elif obj_type == "MESH":
            file_name = data_obj.get("file_name", "cube")
            obj = self.create_mesh_object(name, file_name)
        elif obj_type == "CAMERA":
            bpy.ops.object.camera_add()
            obj = bpy.context.active_object
            obj.name = name
            obj["type"] = "CAMERA"
        elif obj_type == "LIGHT":
            # level_loader.cpp では type == LIGHT の場合、平行光源として追加？
            # Blender上ではSUNやPOINTにする
            bpy.ops.object.light_add(type='SUN')
            obj = bpy.context.active_object
            obj.name = name
            obj["type"] = "LIGHT"
        else:
            # 空のオブジェクトでフォールバック
            obj = bpy.data.objects.new(name, None)
            bpy.context.collection.objects.link(obj)
            
        if obj is None:
            return None

        # カスタムプロパティ
        if "collider" in data_obj:
            collider_data = data_obj["collider"]
            obj["collider"] = collider_data.get("type", "BOX")
            cc = collider_data.get("center", (0, 0, 0))
            cs = collider_data.get("size", (2, 2, 2))
            # コライダーの座標変換 (ゲーム -> Blender)
            obj["collider_center"] = mathutils.Vector((cc[0], cc[2], cc[1]))
            obj["collider_size"] = mathutils.Vector((cs[0], cs[2], cs[1]))
            
        if "disabled" in data_obj:
            obj["disabled"] = int(data_obj["disabled"])
            
        if "spawn_time" in data_obj:
            obj["spawn_time"] = float(data_obj["spawn_time"])
            
        if parent_obj:
            obj.parent = parent_obj
            
        if "transform" in data_obj:
            self.apply_transform(obj, data_obj["transform"])
            
        if "children" in data_obj:
            for child_data in data_obj["children"]:
                self.import_object_recursive(child_data, obj)
                
        return obj

    def import_rail(self, rail_points):
        # 古い "Rail" オブジェクトを削除
        old_rail = bpy.data.objects.get("Rail")
        if old_rail:
            bpy.data.objects.remove(old_rail, do_unlink=True)
            
        # 新しい Curve の生成
        curve_data = bpy.data.curves.new(name="RailData", type='CURVE')
        curve_data.dimensions = '3D'
        
        spline = curve_data.splines.new(type='POLY')
        spline.points.add(len(rail_points) - 1)
        
        for i, pt in enumerate(rail_points):
            # ゲーム座標 [gx, gy, gz] -> Blender [gx, gz, gy]
            gx, gy, gz = pt
            spline.points[i].co = (gx, gz, gy, 1.0)
            
        rail_obj = bpy.data.objects.new("Rail", curve_data)
        bpy.context.collection.objects.link(rail_obj)

    def execute(self, context):
        print(f"シーン情報をインポート中... {self.filepath}")

        if not os.path.exists(self.filepath):
            self.report({'ERROR'}, f"ファイルが存在しません: {self.filepath}")
            return {'CANCELLED'}

        with open(self.filepath, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
            except Exception as e:
                self.report({'ERROR'}, f"JSONの解析に失敗しました: {e}")
                return {'CANCELLED'}

        # シーンオブジェクトをクリア
        self.clear_scene_objects()

        # レールデータの読み込み
        if "rail_spline" in data:
            self.import_rail(data["rail_spline"])
            self.report({'INFO'}, "レール情報を読み込みました")
        else:
            # Fallback
            rail_points = None
            if "objects" in data:
                for obj in data["objects"]:
                    if obj.get("type") == "CURVE" and "control_points" in obj:
                        rail_points = obj["control_points"]
                        break
            if rail_points:
                self.import_rail(rail_points)
                self.report({'INFO'}, "フォールバックによりレール情報を読み込みました")

        # オブジェクトデータの読み込み
        if "objects" in data:
            bpy.ops.object.select_all(action='DESELECT')
            for data_obj in data["objects"]:
                if data_obj.get("type") == "CURVE":
                    continue
                self.import_object_recursive(data_obj)
            self.report({'INFO'}, "オブジェクト情報を読み込みました")

        self.report({'INFO'}, "シーン情報をインポートしました")
        return {'FINISHED'}

classes = (
    MYADDON_OT_import_scene,
)
