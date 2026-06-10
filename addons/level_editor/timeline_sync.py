# ============================================================
# timeline_sync.py — Blender 4.4 タイムトラベルデバッガーアドオン
# ============================================================
#
# ゲームエンジン（C++）の DebugManager と TCP ソケットで通信し、
# オブジェクトの座標同期・タイムライン巻き戻し・変数インスペクション・
# 関数トレース表示を行う Blender アドオンモジュール。
#

import bpy
import socket
import json
import threading
import time
from bpy.props import (
    BoolProperty, IntProperty, StringProperty, FloatProperty
)

# ============================================================
# グローバル状態
# ============================================================

_socket = None           # TCPソケット
_connected = False       # 接続状態
_timer_running = False   # ポーリングタイマー動作中か
_recv_buffer = ""        # 受信バッファ
_suppress_seek = False   # frame_update 受信中のシーク抑制フラグ

# エンジンから受信したデータ
_current_frame = 0
_objects_data = []       # [{"id": str, "model": str, "position": [x,y,z], ...}]
_variables_data = {}     # {"Player": {"HP": "100.0", ...}, ...}
_call_stack_data = []    # [{"func": str, "frame": int, "time_ms": float}]


# ============================================================
# ソケット通信
# ============================================================

def connect_to_engine(host="127.0.0.1", port=9999):
    """エンジンに TCP 接続する"""
    global _socket, _connected, _recv_buffer

    if _connected:
        return True

    try:
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.settimeout(2.0)
        _socket.connect((host, port))
        _socket.setblocking(False)
        _connected = True
        _recv_buffer = ""
        return True
    except Exception as e:
        print(f"[TTD] 接続失敗: {e}")
        _socket = None
        _connected = False
        return False


def disconnect_from_engine():
    """エンジンから切断する"""
    global _socket, _connected, _recv_buffer

    if _socket:
        try:
            _socket.close()
        except Exception:
            pass
    _socket = None
    _connected = False
    _recv_buffer = ""


def send_command(cmd_dict):
    """JSON コマンドをエンジンに送信する"""
    global _socket, _connected

    if not _connected or not _socket:
        return

    try:
        data = json.dumps(cmd_dict) + "\n"
        _socket.sendall(data.encode("utf-8"))
    except Exception as e:
        print(f"[TTD] 送信エラー: {e}")
        disconnect_from_engine()


def receive_data():
    """ノンブロッキングでデータを受信し、メッセージを処理する"""
    global _socket, _connected, _recv_buffer

    if not _connected or not _socket:
        return

    try:
        data = _socket.recv(65536)
        if not data:
            # 接続切断
            disconnect_from_engine()
            return
        _recv_buffer += data.decode("utf-8", errors="replace")

        # 改行区切りでメッセージを分割
        while "\n" in _recv_buffer:
            line, _recv_buffer = _recv_buffer.split("\n", 1)
            if line.strip():
                try:
                    msg = json.loads(line)
                    handle_message(msg)
                except json.JSONDecodeError:
                    pass

    except BlockingIOError:
        pass  # データなし
    except Exception as e:
        print(f"[TTD] 受信エラー: {e}")
        disconnect_from_engine()


def handle_message(msg):
    """エンジンから受信したメッセージを処理する"""
    global _current_frame, _objects_data, _variables_data, _call_stack_data
    global _suppress_seek

    msg_type = msg.get("type", "")

    if msg_type == "frame_update":
        _current_frame = msg.get("frame", 0)
        _objects_data = msg.get("objects", [])
        _variables_data = msg.get("variables", {})
        _call_stack_data = msg.get("call_stack", [])

        # Blender上のオブジェクトを同期
        sync_objects()

        # タイムラインのフレームを更新（自分の seek を抑制）
        _suppress_seek = True
        try:
            scene = bpy.context.scene
            if scene.ttd_live_sync and scene.frame_current != _current_frame:
                scene.frame_set(_current_frame)
        finally:
            _suppress_seek = False

        # UIを更新
        for area in bpy.context.screen.areas:
            area.tag_redraw()


# ============================================================
# オブジェクト同期
# ============================================================

def sync_objects():
    """エンジンのオブジェクトデータを Blender の Empty に反映する"""
    for obj_data in _objects_data:
        obj_id = obj_data.get("id", "")
        if not obj_id:
            continue

        # Blender上に同じ名前のオブジェクトがあるか検索
        blender_name = f"TTD_{obj_id}"
        bl_obj = bpy.data.objects.get(blender_name)

        if bl_obj is None:
            # 自動生成: Empty (Sphere 表示)
            bl_obj = bpy.data.objects.new(blender_name, None)
            bl_obj.empty_display_type = 'SPHERE'
            bl_obj.empty_display_size = 0.5
            bpy.context.scene.collection.objects.link(bl_obj)

        # トランスフォーム同期
        pos = obj_data.get("position", [0, 0, 0])
        rot = obj_data.get("rotation", [0, 0, 0])
        scl = obj_data.get("scale", [1, 1, 1])

        bl_obj.location = (pos[0], pos[2], pos[1])       # Y-up → Z-up 変換
        bl_obj.rotation_euler = (rot[0], rot[2], rot[1])  # 同上
        bl_obj.scale = (scl[0], scl[2], scl[1])

        # デバッグ変数をカスタムプロパティとして保存
        # Object3d のID名と一致する変数グループがあれば紐付け
        var_group = _variables_data.get(obj_id, {})
        for var_name, var_value in var_group.items():
            bl_obj[f"dbg_{var_name}"] = var_value


# ============================================================
# bpy.app.timers によるポーリング
# ============================================================

def polling_timer():
    """16ms 間隔でソケットからデータを受信する"""
    global _timer_running

    if not _timer_running:
        return None  # タイマー停止

    receive_data()
    return 0.016  # 次回呼び出しまで16ms


def start_polling():
    """ポーリングタイマーを開始する"""
    global _timer_running

    if _timer_running:
        return

    _timer_running = True
    bpy.app.timers.register(polling_timer)


def stop_polling():
    """ポーリングタイマーを停止する"""
    global _timer_running
    _timer_running = False


# ============================================================
# タイムラインハンドラ（双方向同期）
# ============================================================

def on_frame_change(scene):
    """Blenderのタイムラインが操作されたときにエンジンに seek を送信する"""
    global _suppress_seek

    if _suppress_seek:
        return

    if not _connected:
        return

    if not scene.ttd_live_sync:
        return

    send_command({"type": "seek", "frame": scene.frame_current})


# ============================================================
# オペレーター
# ============================================================

class TTD_OT_Connect(bpy.types.Operator):
    """エンジンに接続する"""
    bl_idname = "ttd.connect"
    bl_label = "Connect to Engine"

    def execute(self, context):
        if connect_to_engine():
            start_polling()
            self.report({'INFO'}, "エンジンに接続しました")
        else:
            self.report({'ERROR'}, "接続に失敗しました")
        return {'FINISHED'}


class TTD_OT_Disconnect(bpy.types.Operator):
    """エンジンから切断する"""
    bl_idname = "ttd.disconnect"
    bl_label = "Disconnect"

    def execute(self, context):
        stop_polling()
        disconnect_from_engine()
        self.report({'INFO'}, "切断しました")
        return {'FINISHED'}


class TTD_OT_Pause(bpy.types.Operator):
    """ゲームを一時停止する"""
    bl_idname = "ttd.pause"
    bl_label = "Pause"

    def execute(self, context):
        send_command({"type": "pause"})
        self.report({'INFO'}, "一時停止")
        return {'FINISHED'}


class TTD_OT_Resume(bpy.types.Operator):
    """ゲームを再開する"""
    bl_idname = "ttd.resume"
    bl_label = "Resume"

    def execute(self, context):
        send_command({"type": "resume"})
        self.report({'INFO'}, "再開")
        return {'FINISHED'}


class TTD_OT_ExportState(bpy.types.Operator):
    """現在の状態をファイルに保存する"""
    bl_idname = "ttd.export_state"
    bl_label = "Export State"

    def execute(self, context):
        send_command({"type": "export_state", "path": "autosave.state"})
        self.report({'INFO'}, "状態をエクスポートしました")
        return {'FINISHED'}


class TTD_OT_InjectState(bpy.types.Operator):
    """保存した状態を復元する"""
    bl_idname = "ttd.inject_state"
    bl_label = "Inject State"

    def execute(self, context):
        send_command({"type": "inject_state", "path": "autosave.state"})
        self.report({'INFO'}, "状態をインジェクトしました")
        return {'FINISHED'}


# ============================================================
# UIパネル
# ============================================================

class TTD_PT_DebuggerPanel(bpy.types.Panel):
    """メインデバッガーパネル"""
    bl_label = "Time Travel Debugger"
    bl_idname = "TTD_PT_debugger"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Level Editor"

    def draw(self, context):
        layout = self.layout

        # 接続状態
        box = layout.box()
        if _connected:
            box.label(text="Status: Connected", icon='LINKED')
            box.operator("ttd.disconnect", icon='UNLINKED')
        else:
            box.label(text="Status: Disconnected", icon='UNLINKED')
            box.operator("ttd.connect", icon='LINKED')

        layout.separator()

        # Live Sync
        layout.prop(context.scene, "ttd_live_sync", text="Live Sync")

        # フレーム情報
        layout.label(text=f"Frame: {_current_frame}")

        layout.separator()

        # 操作ボタン
        row = layout.row(align=True)
        row.operator("ttd.pause", icon='PAUSE')
        row.operator("ttd.resume", icon='PLAY')

        layout.separator()

        # 状態の保存・復元
        row = layout.row(align=True)
        row.operator("ttd.export_state", icon='EXPORT')
        row.operator("ttd.inject_state", icon='IMPORT')


class TTD_PT_Inspector(bpy.types.Panel):
    """変数インスペクターパネル"""
    bl_label = "Variable Inspector"
    bl_idname = "TTD_PT_inspector"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Level Editor"
    bl_parent_id = "TTD_PT_debugger"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        if not _variables_data:
            layout.label(text="変数データなし", icon='INFO')
            return

        for group_name, variables in _variables_data.items():
            box = layout.box()
            box.label(text=group_name, icon='OBJECT_DATA')

            for var_name, var_value in variables.items():
                row = box.row()
                row.label(text=f"  {var_name}:")
                row.label(text=str(var_value))


class TTD_PT_CallStack(bpy.types.Panel):
    """関数トレース（コールスタック）パネル"""
    bl_label = "Call Stack"
    bl_idname = "TTD_PT_callstack"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Level Editor"
    bl_parent_id = "TTD_PT_debugger"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        if not _call_stack_data:
            layout.label(text="トレースデータなし", icon='INFO')
            return

        for trace in _call_stack_data:
            row = layout.row()
            row.label(text=trace.get("func", "?"), icon='SCRIPT')
            row.label(text=f"{trace.get('time_ms', 0):.1f}ms")


# ============================================================
# 登録
# ============================================================

classes = (
    TTD_OT_Connect,
    TTD_OT_Disconnect,
    TTD_OT_Pause,
    TTD_OT_Resume,
    TTD_OT_ExportState,
    TTD_OT_InjectState,
    TTD_PT_DebuggerPanel,
    TTD_PT_Inspector,
    TTD_PT_CallStack,
)


def register_handlers():
    """フレーム変更ハンドラとシーンプロパティを登録する"""
    bpy.types.Scene.ttd_live_sync = BoolProperty(
        name="Live Sync",
        description="エンジンのフレームとBlenderのタイムラインを同期する",
        default=True
    )

    if on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(on_frame_change)


def unregister_handlers():
    """フレーム変更ハンドラとシーンプロパティを解除する"""
    stop_polling()
    disconnect_from_engine()

    if on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(on_frame_change)

    if hasattr(bpy.types.Scene, "ttd_live_sync"):
        del bpy.types.Scene.ttd_live_sync
