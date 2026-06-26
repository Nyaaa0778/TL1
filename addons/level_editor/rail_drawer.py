import bpy
import gpu
import mathutils
import math

def catmull_rom_spline(points, index, t):
    n = len(points)
    if n == 0:
        return mathutils.Vector((0.0, 0.0, 0.0))
    if n == 1:
        return points[0]

    i0 = 0 if index == 0 else index - 1
    i1 = index
    i2 = min(n - 1, index + 1)
    i3 = min(n - 1, index + 2)

    p0 = points[i0]
    p1 = points[i1]
    p2 = points[i2]
    p3 = points[i3]

    t2 = t * t
    t3 = t2 * t

    a = p1 * 2.0
    b = (p2 - p0) * t
    c = (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
    d = (p0 * -1.0 + p1 * 3.0 - p2 * 3.0 + p3) * t3

    return (a + b + c + d) * 0.5

def evaluate_spline(points, time):
    n = len(points)
    if n == 0:
        return mathutils.Vector((0.0, 0.0, 0.0))
    if n == 1:
        return points[0]

    segment_index = int(time)
    if segment_index >= n - 1:
        segment_index = n - 2
        t = 1.0
    else:
        t = time - segment_index

    return catmull_rom_spline(points, segment_index, t)

class DrawRail:
    handle = None

    @staticmethod
    def draw_rail():
        # シーン内の "Rail" オブジェクトを探す
        rail_obj = bpy.context.scene.objects.get("Rail")
        if not rail_obj or rail_obj.type != 'CURVE':
            return

        # 制御点のワールド座標を抽出
        points = []
        for spline in rail_obj.data.splines:
            if spline.type in {'POLY', 'NURBS'}:
                for pt in spline.points:
                    wpos = rail_obj.matrix_world @ pt.co.xyz
                    points.append(wpos)
            elif spline.type == 'BEZIER':
                for pt in spline.bezier_points:
                    wpos = rail_obj.matrix_world @ pt.co
                    points.append(wpos)

        n = len(points)
        if n < 2:
            return

        # スプライン補間点群の計算
        vertices = []
        segments = (n - 1) * 30  # 各セグメントを30分割
        for i in range(segments + 1):
            time = (i / segments) * (n - 1)
            v = evaluate_spline(points, time)
            vertices.append(v)

        # 描画処理
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        
        fmt = gpu.types.GPUVertFormat()
        fmt.attr_add(id="pos", comp_type="F32", len=3, fetch_mode="FLOAT")
        
        vbo = gpu.types.GPUVertBuf(len=len(vertices), format=fmt)
        vbo.attr_fill(id="pos", data=vertices)
        
        # インデックスバッファなしで LINE_STRIP 描画
        batch = gpu.types.GPUBatch(type="LINE_STRIP", buf=vbo)
        
        shader.bind()
        # 水色 (0.0, 0.8, 1.0, 1.0)
        shader.uniform_float("color", [0.0, 0.8, 1.0, 1.0])
        
        try:
            # 線の太さを設定 (非推奨警告を避けるため try-except)
            gpu.state.line_width_set(3.0)
        except AttributeError:
            pass

        batch.draw(shader)

def register_handlers():
    if DrawRail.handle is None:
        DrawRail.handle = bpy.types.SpaceView3D.draw_handler_add(
            DrawRail.draw_rail, (), "WINDOW", "POST_VIEW"
        )

def unregister_handlers():
    if DrawRail.handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DrawRail.handle, "WINDOW")
        DrawRail.handle = None

classes = ()
