import bpy
import mathutils
from .rail_drawer import evaluate_spline

# -----------------------------------------------------------------------------
# オペレーター定義
# -----------------------------------------------------------------------------

class MYADDON_OT_select_scene_object(bpy.types.Operator):
    bl_idname = "myaddon.select_scene_object"
    bl_label = "オブジェクトを選択"
    bl_description = "指定されたオブジェクトを選択状態にし、アクティブにします"
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if obj:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


class MYADDON_OT_delete_scene_object(bpy.types.Operator):
    bl_idname = "myaddon.delete_scene_object"
    bl_label = "オブジェクトを削除"
    bl_description = "指定されたオブジェクトをシーンおよびデータから完全に削除します"
    bl_options = {"REGISTER", "UNDO"}
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
            self.report({'INFO'}, f"{self.object_name} を削除しました")
        return {'FINISHED'}


class MYADDON_OT_add_spawn_time(bpy.types.Operator):
    bl_idname = "myaddon.add_spawn_time"
    bl_label = "出現時間プロパティ追加"
    bl_description = "['spawn_time'] カスタムプロパティを追加します"
    bl_options = {"REGISTER", "UNDO"}
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if obj:
            obj["spawn_time"] = 0.0
        return {'FINISHED'}


class MYADDON_OT_calc_closest_spawn_time(bpy.types.Operator):
    bl_idname = "myaddon.calc_closest_spawn_time"
    bl_label = "最寄りのレール位置から時間を計算"
    bl_description = "このオブジェクトに最も近いレール上の位置から、最適な出現時間を自動計算します"
    bl_options = {"REGISTER", "UNDO"}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if not obj:
            self.report({'WARNING'}, "オブジェクトが見つかりません")
            return {'CANCELLED'}

        rail_obj = context.scene.objects.get("Rail")
        if not rail_obj or rail_obj.type != 'CURVE':
            self.report({'WARNING'}, "Railオブジェクト(CURVE)が見つかりません")
            return {'CANCELLED'}

        # 制御点のワールド座標を抽出
        points = []
        for spline in rail_obj.data.splines:
            if spline.type in {'POLY', 'NURBS'}:
                for pt in spline.points:
                    points.append(rail_obj.matrix_world @ pt.co.xyz)
            elif spline.type == 'BEZIER':
                for pt in spline.bezier_points:
                    points.append(rail_obj.matrix_world @ pt.co)

        n = len(points)
        if n < 2:
            self.report({'WARNING'}, "Railの制御点が足りません")
            return {'CANCELLED'}

        # エネミーの位置から最短のスプライン媒介変数tを探索
        enemy_pos = obj.matrix_world.translation
        best_t = 0.0
        min_dist = float('inf')
        
        # 二段階で探索（粗探索 -> 詳細探索）
        steps = (n - 1) * 100
        for i in range(steps + 1):
            t = (i / steps) * (n - 1)
            p = evaluate_spline(points, t)
            dist = (p - enemy_pos).length
            if dist < min_dist:
                min_dist = dist
                best_t = t

        # Offset を引いて手前で出現させる
        offset = getattr(context.scene, "spawn_time_offset", 0.5)
        obj["spawn_time"] = max(0.0, best_t - offset)
        self.report({'INFO'}, f"{obj.name} の出現時間をレール位置 {best_t:.3f} (オフセット引いて {obj['spawn_time']:.3f}) に自動設定しました。")
        return {"FINISHED"}


class MYADDON_OT_auto_calc_all_spawn_times(bpy.types.Operator):
    bl_idname = "myaddon.auto_calc_all_spawn_times"
    bl_label = "全敵の出現時間を自動計算"
    bl_description = "シーン内のすべての敵について、レール上の最寄り位置から出現時間を一括で自動計算します"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        rail_obj = context.scene.objects.get("Rail")
        if not rail_obj or rail_obj.type != 'CURVE':
            self.report({'WARNING'}, "Railオブジェクトが見つかりません")
            return {'CANCELLED'}
            
        points = []
        for spline in rail_obj.data.splines:
            if spline.type in {'POLY', 'NURBS'}:
                for pt in spline.points:
                    points.append(rail_obj.matrix_world @ pt.co.xyz)
            elif spline.type == 'BEZIER':
                for pt in spline.bezier_points:
                    points.append(rail_obj.matrix_world @ pt.co)
                    
        n = len(points)
        if n < 2:
            self.report({'WARNING'}, "Railの制御点が足りません")
            return {'CANCELLED'}
            
        count = 0
        for obj in context.scene.objects:
            if obj.get("type") == "PlayerSpawn" and "Enemy" in obj.name:
                enemy_pos = obj.matrix_world.translation
                best_t = 0.0
                min_dist = float('inf')
                steps = (n - 1) * 100
                for i in range(steps + 1):
                    t = (i / steps) * (n - 1)
                    p = evaluate_spline(points, t)
                    dist = (p - enemy_pos).length
                    if dist < min_dist:
                        min_dist = dist
                        best_t = t
                offset = getattr(context.scene, "spawn_time_offset", 0.5)
                obj["spawn_time"] = max(0.0, best_t - offset)
                count += 1
                
        self.report({'INFO'}, f"計 {count} 個のエネミーの出現時間を自動計算（オフセット適用）しました。")
        return {'FINISHED'}


class MYADDON_OT_set_spawn_time_current_frame(bpy.types.Operator):
    bl_idname = "myaddon.set_spawn_time_current_frame"
    bl_label = "現フレームを出現時間に設定"
    bl_description = "現在のフレームから出現時間を計算し、設定します"
    bl_options = {"REGISTER", "UNDO"}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        
        frames_per_segment = context.scene.timeline_frames_per_segment
        if frames_per_segment <= 0.001:
            frames_per_segment = 100.0
            
        obj["spawn_time"] = context.scene.frame_current / frames_per_segment
        self.report({'INFO'}, f"{obj.name} の出現時間を現フレームから {obj['spawn_time']:.3f} に設定しました。")
        return {"FINISHED"}


class MYADDON_OT_jump_to_spawn_time(bpy.types.Operator):
    bl_idname = "myaddon.jump_to_spawn_time"
    bl_label = "出現フレームにジャンプ"
    bl_description = "Blenderのタイムラインをこのオブジェクトの出現フレームに合わせます"
    bl_options = {"REGISTER", "UNDO"}

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.scene.objects.get(self.object_name)
        if not obj or "spawn_time" not in obj:
            return {'CANCELLED'}
        
        frames_per_segment = context.scene.timeline_frames_per_segment
        target_frame = int(obj["spawn_time"] * frames_per_segment)
        context.scene.frame_set(target_frame)
        return {"FINISHED"}


class MYADDON_OT_create_enemy_at_current_frame(bpy.types.Operator):
    bl_idname = "myaddon.create_enemy_at_current_frame"
    bl_label = "現フレーム位置に敵を作成"
    bl_description = "3Dカーソル位置にエネミー出現ポイントを作成し、出現時間を現フレームに設定します"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        # 既存のエネミー出現ポイント作成処理を呼び出し
        bpy.ops.myaddon.spawn_enemy_create_symbol('EXEC_DEFAULT')
        obj = context.active_object
        if obj:
            # 3Dカーソル位置に配置
            obj.location = context.scene.cursor.location
            frames_per_segment = context.scene.timeline_frames_per_segment
            if frames_per_segment <= 0.001:
                frames_per_segment = 100.0
            # 出現時間を現在のフレーム値で設定
            obj["spawn_time"] = context.scene.frame_current / frames_per_segment
            self.report({'INFO'}, f"新規エネミーを生成し、出現時間を {obj['spawn_time']:.3f} に設定しました。")
        return {'FINISHED'}

# -----------------------------------------------------------------------------
# プレビューカメラ制御とタイムラインハンドラー
# -----------------------------------------------------------------------------

def preview_camera_handler(scene):
    if not scene.preview_camera_follows_rail:
        return
        
    rail_obj = scene.objects.get("Rail")
    if not rail_obj or rail_obj.type != 'CURVE':
        return
        
    points = []
    for spline in rail_obj.data.splines:
        if spline.type in {'POLY', 'NURBS'}:
            for pt in spline.points:
                points.append(rail_obj.matrix_world @ pt.co.xyz)
        elif spline.type == 'BEZIER':
            for pt in spline.bezier_points:
                points.append(rail_obj.matrix_world @ pt.co)
                
    n = len(points)
    if n < 2:
        return
        
    frames_per_segment = scene.timeline_frames_per_segment
    if frames_per_segment <= 0.001:
        frames_per_segment = 100.0
        
    spline_time = scene.frame_current / frames_per_segment
    spline_time = max(0.0, min(float(n - 1), spline_time))
    
    # 座標の補間
    pos = evaluate_spline(points, spline_time)
    
    # プレビューカメラオブジェクトの取得・作成
    cam_name = "PreviewCamera"
    cam_obj = scene.objects.get(cam_name)
    if not cam_obj:
        cam_data = bpy.data.cameras.new(name=cam_name)
        cam_obj = bpy.data.objects.new(cam_name, cam_data)
        scene.collection.objects.link(cam_obj)
        
    cam_obj.location = pos
    
    # 接線からカメラの回転を計算（進行方向を向くように）
    t_ahead = spline_time + 0.01
    if t_ahead >= n - 1:
        t_ahead = spline_time - 0.01
        pos_behind = evaluate_spline(points, t_ahead)
        direction = pos - pos_behind
    else:
        pos_ahead = evaluate_spline(points, t_ahead)
        direction = pos_ahead - pos
        
    if direction.length > 0.0001:
        # Blenderのカメラはローカル-Zが前方、Yが上
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

# -----------------------------------------------------------------------------
# UI パネル定義
# -----------------------------------------------------------------------------

class VIEW3D_PT_spawn_timeline_editor(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LevelEditor'
    bl_label = "Spawn Timeline Editor"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # グローバル設定
        box = layout.box()
        box.label(text="Timeline Configuration", icon='TIME')
        box.prop(scene, "timeline_frames_per_segment")
        box.prop(scene, "spawn_time_offset")
        box.prop(scene, "preview_camera_follows_rail")

        # 一括編集・作成用
        row = layout.row(align=True)
        row.operator("myaddon.create_enemy_at_current_frame", text="現在フレームで敵を作成", icon='ADD')
        row.operator("myaddon.auto_calc_all_spawn_times", text="全エネミー時間を自動計算", icon='TRACKING')

        # エネミー一覧
        enemies = []
        for obj in scene.objects:
            if obj.get("type") == "PlayerSpawn" and "Enemy" in obj.name:
                enemies.append(obj)
        
        # 出現時間でソート
        enemies.sort(key=lambda o: o.get("spawn_time", 0.0))

        layout.separator()
        layout.label(text=f"Enemies Timeline List ({len(enemies)}):", icon='ANIM')
        
        col = layout.column(align=True)
        for obj in enemies:
            row = col.box().row(align=True)
            
            # 選択状況に応じたアイコン
            is_active = (context.active_object == obj)
            icon = 'OBJECT_DATAMODE' if is_active else 'OBJECT_DATA'
            
            # 選択ボタン
            op_select = row.operator("myaddon.select_scene_object", text=obj.name, icon=icon, emboss=False)
            op_select.object_name = obj.name
            
            # 出現時間（カスタムプロパティ）の直接編集
            if "spawn_time" in obj:
                row.prop(obj, '["spawn_time"]', text="Time")
            else:
                op_add = row.operator("myaddon.add_spawn_time", text="Add Time")
                op_add.object_name = obj.name
            
            # フレーム表示とジャンプ・同期ボタン
            frames_per_segment = scene.timeline_frames_per_segment
            if frames_per_segment <= 0.001:
                frames_per_segment = 100.0
            frame_val = int(obj.get("spawn_time", 0.0) * frames_per_segment)
            
            op_jump = row.operator("myaddon.jump_to_spawn_time", text=f"F: {frame_val}", icon='TIME')
            op_jump.object_name = obj.name
            
            op_set = row.operator("myaddon.set_spawn_time_current_frame", text="", icon='REC')
            op_set.object_name = obj.name

            op_calc = row.operator("myaddon.calc_closest_spawn_time", text="", icon='TRACKING_BACKWARDS')
            op_calc.object_name = obj.name
            
            op_del = row.operator("myaddon.delete_scene_object", text="", icon='TRASH')
            op_del.object_name = obj.name

# -----------------------------------------------------------------------------
# 登録処理
# -----------------------------------------------------------------------------

classes = (
    MYADDON_OT_select_scene_object,
    MYADDON_OT_delete_scene_object,
    MYADDON_OT_add_spawn_time,
    MYADDON_OT_calc_closest_spawn_time,
    MYADDON_OT_auto_calc_all_spawn_times,
    MYADDON_OT_set_spawn_time_current_frame,
    MYADDON_OT_jump_to_spawn_time,
    MYADDON_OT_create_enemy_at_current_frame,
    VIEW3D_PT_spawn_timeline_editor,
)

def register():
    bpy.types.Scene.timeline_frames_per_segment = bpy.props.FloatProperty(
        name="Frames / Segment",
        description="レール1セグメントあたりのフレーム数",
        default=100.0,
        min=1.0
    )
    bpy.types.Scene.preview_camera_follows_rail = bpy.props.BoolProperty(
        name="Preview Cam Follows Rail",
        description="タイムラインのフレーム変更に合わせてプレビューカメラをレールに沿って移動させる",
        default=False
    )
    bpy.types.Scene.spawn_time_offset = bpy.props.FloatProperty(
        name="Spawn Time Offset",
        description="最寄り位置からこの値だけ前倒しして（手前で）敵を出現させます（レールセグメント単位）",
        default=0.5,
        min=0.0
    )
    
    if preview_camera_handler not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(preview_camera_handler)
        
    print("timeline_editor: registered properties & handlers")

def unregister():
    if preview_camera_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(preview_camera_handler)
        
    del bpy.types.Scene.timeline_frames_per_segment
    del bpy.types.Scene.preview_camera_follows_rail
    del bpy.types.Scene.spawn_time_offset
    print("timeline_editor: unregistered properties & handlers")
