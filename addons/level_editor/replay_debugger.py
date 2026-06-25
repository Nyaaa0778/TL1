import bpy
import json
import os
import socket
import blf
from bpy_extras.view3d_utils import location_3d_to_region_2d

# グローバル状態保持用
loaded_replay_data = None
draw_handler_handle = None

class TCPClient:
    def __init__(self):
        self.sock = None
        
    def connect(self, ip, port):
        self.disconnect()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(0.5)
            self.sock.connect((ip, port))
            return True
        except Exception as e:
            print("[TCPClient] Connect failed:", e)
            self.sock = None
            return False
            
    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
            
    def is_connected(self):
        return self.sock is not None
        
    def send(self, msg):
        if self.sock:
            try:
                self.sock.sendall(msg.encode('utf-8'))
            except Exception as e:
                print("[TCPClient] Send failed:", e)
                self.disconnect()

# グローバルTCPクライアント
client = TCPClient()

def set_material_color(mat, color):
    mat.use_nodes = True
    principled = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if principled:
        principled.inputs[0].default_value = color

def update_thread_curve(frame_idx):
    global loaded_replay_data
    if not loaded_replay_data:
        return
        
    frames = loaded_replay_data.get("frames", [])
    game_frame = frame_idx - 1 # 0-indexed game frame
    
    if game_frame < 0 or game_frame >= len(frames):
        return
        
    frame_data = frames[game_frame]
    thread_nodes = frame_data.get("thread_nodes", [])
    
    curve_obj = bpy.data.objects.get("PlayerThread")
    if not curve_obj:
        return
        
    curve_data = curve_obj.data
    curve_data.splines.clear()
    
    if len(thread_nodes) > 0:
        polyline = curve_data.splines.new('POLY')
        polyline.points.add(len(thread_nodes) - 1)
        for i, node in enumerate(thread_nodes):
            polyline.points[i].co = (node[0], node[2], node[1], 1.0)

# タイムライン変更イベントハンドラ
def frame_change_handler(scene):
    frame_idx = scene.frame_current
    update_thread_curve(frame_idx)
    update_custom_properties(frame_idx)
    
    global client
    if client.is_connected():
        game_frame = frame_idx - 1
        if game_frame < 0:
            game_frame = 0
        client.send(f"FRAME {game_frame}\n")

def update_custom_properties(frame_idx):
    global loaded_replay_data
    if not loaded_replay_data:
        return
        
    frames = loaded_replay_data.get("frames", [])
    game_frame = frame_idx - 1
    
    if game_frame < 0 or game_frame >= len(frames):
        return
        
    frame_data = frames[game_frame]
    enemies = frame_data.get("enemies", [])
    events = frame_data.get("events", {})
    bug_triggered = events.get("bug_trigger", False)
    
    # プレイヤーのカスタムプロパティ更新
    player_obj = bpy.data.objects.get("DebugPlayer")
    if player_obj:
        player_obj["bug_triggered"] = bug_triggered
        if bug_triggered:
            player_obj["bug_message"] = events.get("msg", "")
        else:
            player_obj["bug_message"] = ""
            
    # 敵のカスタムプロパティ更新
    for enemy in enemies:
        idx = enemy.get("index", 0)
        e_obj = bpy.data.objects.get(f"DebugEnemy_{idx}")
        if e_obj:
            e_obj["hp"] = enemy.get("hp", 100.0)
            e_obj["anim_state"] = enemy.get("anim_state", "")
            e_obj["bug_triggered"] = bug_triggered

# ビューポートオーバーレイテキスト描画ハンドラ
def draw_callback_px(self, context):
    global loaded_replay_data
    if not loaded_replay_data:
        return
        
    # context が None の場合の安全なフォールバック
    if context is None:
        context = bpy.context
        
    # scene の取得
    scene = getattr(context, "scene", None)
    if not scene:
        scene = bpy.context.scene
        
    frame_idx = scene.frame_current
    game_frame = frame_idx - 1
    frames = loaded_replay_data.get("frames", [])
    
    if game_frame < 0 or game_frame >= len(frames):
        return
        
    frame_data = frames[game_frame]
    enemies = frame_data.get("enemies", [])
    events = frame_data.get("events", {})
    
    font_id = 0
    blf.size(font_id, 16)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
    
    # ヘッダー描画 (画面固定)
    blf.position(font_id, 20, 120, 0)
    blf.draw(font_id, "=== Live Game Replay Monitor ===")
    
    # バグ状態表示
    bug_triggered = events.get("bug_trigger", False)
    if bug_triggered:
        blf.color(font_id, 1.0, 0.2, 0.2, 1.0) # 赤色
        blf.position(font_id, 20, 95, 0)
        blf.draw(font_id, f"BUG DETECTED: {events.get('msg', 'Collision')}")
    else:
        blf.color(font_id, 0.2, 1.0, 0.2, 1.0) # 緑色
        blf.position(font_id, 20, 95, 0)
        blf.draw(font_id, "Status: OK (Normal Execution)")
        
    # 画面左下の敵キャラ簡易リスト表示
    blf.color(font_id, 0.9, 0.9, 0.9, 1.0)
    y_pos = 70
    for enemy in enemies:
        idx = enemy.get("index", 0)
        hp = enemy.get("hp", 100.0)
        state = enemy.get("anim_state", "")
        blf.position(font_id, 20, y_pos, 0)
        blf.draw(font_id, f"Enemy {idx} HP: {hp:.1f} (Anim: {state})")
        y_pos -= 20

    # 3D空間上の各オブジェクトの頭上に変数を描画
    region = None
    rv3d = None
    
    # context から直接の取得を試みる
    if hasattr(context, "region") and hasattr(context, "space_data") and context.space_data and context.space_data.type == 'VIEW_3D':
        region = context.region
        rv3d = context.space_data.region_3d
    else:
        # コンテキストが描画領域外の可能性を考慮し、画面全体からアクティブな3Dビューポートを探す
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for reg in area.regions:
                    if reg.type == 'WINDOW':
                        region = reg
                        rv3d = area.spaces.active.region_3d
                        break
                if region:
                    break

    if not region or not rv3d:
        return

    # Playerの頭上表示
    player_obj = bpy.data.objects.get("DebugPlayer")
    if player_obj:
        loc_3d = player_obj.location.copy()
        loc_3d.z += 1.2 # Z-upでの高さオフセット
        loc_2d = location_3d_to_region_2d(region, rv3d, loc_3d)
        if loc_2d:
            blf.size(font_id, 14)
            blf.color(font_id, 0.3, 0.8, 1.0, 1.0) # シアン
            blf.position(font_id, loc_2d.x - 30, loc_2d.y, 0)
            blf.draw(font_id, "[Player]")
            
            # バグ検出時は警告も併記
            if bug_triggered:
                blf.size(font_id, 12)
                blf.color(font_id, 1.0, 0.2, 0.2, 1.0)
                blf.position(font_id, loc_2d.x - 50, loc_2d.y - 15, 0)
                blf.draw(font_id, "! BUG AFFECTED !")

    # 各Enemyの頭上表示
    for enemy in enemies:
        idx = enemy.get("index", 0)
        e_obj = bpy.data.objects.get(f"DebugEnemy_{idx}")
        if e_obj:
            loc_3d = e_obj.location.copy()
            loc_3d.z += 1.0
            loc_2d = location_3d_to_region_2d(region, rv3d, loc_3d)
            if loc_2d:
                hp = enemy.get("hp", 100.0)
                state = enemy.get("anim_state", "")
                
                # HP量に応じてカラー変化 (緑 -> 黄 -> 赤)
                if hp > 50.0:
                    blf.color(font_id, 0.2, 1.0, 0.2, 1.0) # 緑
                elif hp > 20.0:
                    blf.color(font_id, 1.0, 0.7, 0.2, 1.0) # 黄色/オレンジ
                else:
                    blf.color(font_id, 1.0, 0.2, 0.2, 1.0) # 赤
                
                blf.size(font_id, 13)
                blf.position(font_id, loc_2d.x - 40, loc_2d.y + 15, 0)
                blf.draw(font_id, f"Enemy {idx}")
                
                blf.color(font_id, 0.9, 0.9, 0.9, 1.0)
                blf.position(font_id, loc_2d.x - 40, loc_2d.y, 0)
                blf.draw(font_id, f"HP: {hp:.1f}")
                
                blf.color(font_id, 0.7, 0.7, 0.7, 1.0)
                blf.position(font_id, loc_2d.x - 40, loc_2d.y - 15, 0)
                blf.draw(font_id, f"Anim: {state}")
                
                if bug_triggered and state == "bugged":
                    blf.color(font_id, 1.0, 0.1, 0.1, 1.0)
                    blf.position(font_id, loc_2d.x - 45, loc_2d.y - 30, 0)
                    blf.draw(font_id, "! BUG SOURCE !")

# ------------------------------------------------------------------------
# 演算オペレータ
# ------------------------------------------------------------------------

class IMPORT_OT_replay_json(bpy.types.Operator):
    bl_label = "Import Replay Log JSON"
    bl_idname = "import.replay_json"
    bl_description = "Loads replay JSON log and rebuilds the animation timeline"

    def execute(self, context):
        global loaded_replay_data
        
        filepath = bpy.path.abspath(context.scene.replay_filepath)
        if not os.path.exists(filepath):
            # プロジェクトフォルダの絶対パスへのフォールバック
            fallback = os.path.join("c:\\Class\\GE3\\CG2\\project", context.scene.replay_filepath.replace("/", os.sep).replace("\\", os.sep))
            if os.path.exists(fallback):
                filepath = fallback
            else:
                self.report({'ERROR'}, f"File not found: {filepath} (Tried fallback: {fallback})")
                return {'CANCELLED'}
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                loaded_replay_data = json.load(f)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to parse JSON: {e}")
            return {'CANCELLED'}
            
        self.report({'INFO'}, "Successfully loaded replay JSON log.")
        
        # 以前のデバッグオブジェクトを破棄
        for obj in list(bpy.data.objects):
            if obj.name.startswith("DebugStatic_") or obj.name.startswith("DebugEnemy_") or obj.name == "PlayerThread" or obj.name == "DebugPlayer":
                bpy.data.objects.remove(obj, do_unlink=True)
                
        snapshot = loaded_replay_data.get("snapshot", {})
        
        # スナップショット配置
        for i, sobj in enumerate(snapshot.get("static_objects", [])):
            name = sobj.get("name", "Cube")
            filename = sobj.get("file_name", "cube")
            t = sobj.get("translation", [0,0,0])
            r = sobj.get("rotation", [0,0,0])
            s = sobj.get("scaling", [1,1,1])
            
            # Y and Z axes swap to map DirectX Y-up coordinates to Blender Z-up coordinates
            loc_swapped = (t[0], t[2], t[1])
            rot_swapped = (r[0], r[2], r[1])
            scale_swapped = (s[0], s[2], s[1])
            
            if "sphere" in filename.lower():
                bpy.ops.mesh.primitive_uv_sphere_add(location=loc_swapped)
            else:
                bpy.ops.mesh.primitive_cube_add(location=loc_swapped)
                
            bobj = bpy.context.active_object
            bobj.name = f"DebugStatic_{name}_{i}"
            bobj.rotation_euler = rot_swapped
            bobj.scale = scale_swapped
            
        # プレイヤー生成
        bpy.ops.mesh.primitive_uv_sphere_add(location=[0,0,0])
        player_obj = bpy.context.active_object
        player_obj.name = "DebugPlayer"
        player_obj.scale = [0.8, 0.8, 0.8]
        
        mat_player = bpy.data.materials.new(name="PlayerMat")
        set_material_color(mat_player, (1.0, 1.0, 1.0, 1.0))
        player_obj.data.materials.append(mat_player)
        
        # 糸用カーブ生成
        curve_data = bpy.data.curves.new('PlayerThreadCurve', type='CURVE')
        curve_data.dimensions = '3D'
        curve_data.bevel_depth = 0.05
        curve_obj = bpy.data.objects.new('PlayerThread', curve_data)
        bpy.context.scene.collection.objects.link(curve_obj)
        
        mat_thread = bpy.data.materials.new(name="ThreadMat")
        set_material_color(mat_thread, (1.0, 0.5, 0.0, 1.0))
        curve_obj.data.materials.append(mat_thread)

        frames = loaded_replay_data.get("frames", [])
        if not frames:
            return {'FINISHED'}
            
        context.scene.frame_start = 1
        context.scene.frame_end = len(frames)
        context.scene.frame_current = 1
        
        enemy_objs = {}
        for f in frames:
            frame_idx = f.get("frame", 0) + 1
            
            p_data = f.get("player", {})
            pt = p_data.get("translation", [0,0,0])
            pr = p_data.get("rotation", [0,0,0])
            
            player_obj.location = (pt[0], pt[2], pt[1])
            player_obj.rotation_euler = (pr[0], pr[2], pr[1])
            player_obj.keyframe_insert(data_path="location", frame=frame_idx)
            player_obj.keyframe_insert(data_path="rotation_euler", frame=frame_idx)
            
            for enemy in f.get("enemies", []):
                idx = enemy.get("index", 0)
                et = enemy.get("translation", [0,0,0])
                er = enemy.get("rotation", [0,0,0])
                
                e_name = f"DebugEnemy_{idx}"
                et_swapped = (et[0], et[2], et[1])
                er_swapped = (er[0], er[2], er[1])
                if e_name not in enemy_objs:
                    bpy.ops.mesh.primitive_uv_sphere_add(location=et_swapped)
                    e_obj = bpy.context.active_object
                    e_obj.name = e_name
                    e_obj.scale = [0.6, 0.6, 0.6]
                    
                    mat_enemy = bpy.data.materials.new(name=f"EnemyMat_{idx}")
                    set_material_color(mat_enemy, (1.0, 0.2, 0.2, 1.0))
                    e_obj.data.materials.append(mat_enemy)
                    enemy_objs[e_name] = e_obj
                else:
                    e_obj = enemy_objs[e_name]
                    
                e_obj.location = et_swapped
                e_obj.rotation_euler = er_swapped
                e_obj.keyframe_insert(data_path="location", frame=frame_idx)
                e_obj.keyframe_insert(data_path="rotation_euler", frame=frame_idx)
                
        update_thread_curve(1)
        update_custom_properties(1)
        return {'FINISHED'}

class CONNECT_OT_game_server(bpy.types.Operator):
    bl_label = "Connect to Game Server"
    bl_idname = "connect.game_server"
    bl_description = "Connects to game engine socket server to synchronize timeline"

    def execute(self, context):
        global client
        ip = context.scene.socket_ip
        port = context.scene.socket_port
        
        if client.connect(ip, port):
            context.scene.socket_connected = True
            self.report({'INFO'}, "Successfully connected to Game Engine TCP Server.")
            
            # ロード中のリプレイログのパスを送信
            rel_path = context.scene.replay_filepath
            client.send(f"LOAD {rel_path}\n")
            
            # 現在のフレームに同期させる
            frame_idx = context.scene.frame_current
            game_frame = frame_idx - 1
            if game_frame < 0:
                game_frame = 0
            client.send(f"FRAME {game_frame}\n")
        else:
            context.scene.socket_connected = False
            self.report({'ERROR'}, f"Failed to connect to Game Engine at {ip}:{port}")
            
        return {'FINISHED'}

class DISCONNECT_OT_game_server(bpy.types.Operator):
    bl_label = "Disconnect Server"
    bl_idname = "disconnect.game_server"
    bl_description = "Closes connection with game engine socket server"

    def execute(self, context):
        global client
        client.disconnect()
        context.scene.socket_connected = False
        self.report({'INFO'}, "Disconnected from Game Engine Server.")
        return {'FINISHED'}

class TAKEOVER_OT_game_state(bpy.types.Operator):
    bl_label = "Takeover Gameplay Now"
    bl_idname = "takeover.game_state"
    bl_description = "Resumes live game control from the current timeline state"

    def execute(self, context):
        global client
        if client.is_connected():
            client.send("TAKEOVER\n")
            self.report({'INFO'}, "Sent TAKEOVER signal to Game Engine.")
        else:
            self.report({'WARNING'}, "Cannot takeover. Socket is not connected.")
        return {'FINISHED'}

class VIEW3D_PT_game_debugger(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LevelEditor' # 既存の LevelEditor のタブに結合します
    bl_label = "Timeline & State Debugger"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        box = layout.box()
        box.label(text="Replay Log JSON File", icon='FILE_FOLDER')
        box.prop(scene, "replay_filepath", text="")
        box.operator("import.replay_json", icon='ANIM_DATA')
        
        box = layout.box()
        box.label(text="Socket Synchronization (TCP)", icon='WORLD')
        box.prop(scene, "socket_ip")
        box.prop(scene, "socket_port")
        
        if not scene.socket_connected:
            box.operator("connect.game_server", icon='PLAY')
        else:
            box.operator("disconnect.game_server", icon='PAUSE')
            box.operator("takeover.game_state", icon='FORWARD')
            
        if loaded_replay_data:
            box = layout.box()
            box.label(text="Replay Info", icon='INFO')
            frames = loaded_replay_data.get("frames", [])
            box.label(text=f"Total frames: {len(frames)}")
            curr_frame = scene.frame_current
            game_frame = curr_frame - 1
            if 0 <= game_frame < len(frames):
                f_data = frames[game_frame]
                events = f_data.get("events", {})
                if events.get("bug_trigger", False):
                    box.alert = True
                    box.label(text=f"BUG DETECTED at frame {curr_frame}!", icon='ERROR')
                    box.label(text=f"Msg: {events.get('msg')}")
                else:
                    box.label(text="Status: No bugs in current frame", icon='CHECKMARK')

classes = (
    IMPORT_OT_replay_json,
    CONNECT_OT_game_server,
    DISCONNECT_OT_game_server,
    TAKEOVER_OT_game_state,
    VIEW3D_PT_game_debugger,
)

def register_handlers():
    # シーンプロパティ定義
    bpy.types.Scene.replay_filepath = bpy.props.StringProperty(
        name="Log Filepath",
        default="logs/play_log.json",
        description="Path to play log JSON file",
        subtype='FILE_PATH'
    )
    bpy.types.Scene.socket_ip = bpy.props.StringProperty(
        name="IP",
        default="127.0.0.1",
        description="IP address of Game Engine TCP Server"
    )
    bpy.types.Scene.socket_port = bpy.props.IntProperty(
        name="Port",
        default=12345,
        description="Port of Game Engine TCP Server"
    )
    bpy.types.Scene.socket_connected = bpy.props.BoolProperty(
        name="Connected",
        default=False
    )
    
    # ハンドラ登録
    if frame_change_handler not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(frame_change_handler)
        
    global draw_handler_handle
    if draw_handler_handle is None:
        draw_handler_handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (None, None), 'WINDOW', 'POST_PIXEL')

def unregister_handlers():
    global client
    client.disconnect()
    
    if frame_change_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(frame_change_handler)
        
    global draw_handler_handle
    if draw_handler_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler_handle, 'WINDOW')
        draw_handler_handle = None
        
    if hasattr(bpy.types.Scene, "replay_filepath"):
        del bpy.types.Scene.replay_filepath
    if hasattr(bpy.types.Scene, "socket_ip"):
        del bpy.types.Scene.socket_ip
    if hasattr(bpy.types.Scene, "socket_port"):
        del bpy.types.Scene.socket_port
    if hasattr(bpy.types.Scene, "socket_connected"):
        del bpy.types.Scene.socket_connected
