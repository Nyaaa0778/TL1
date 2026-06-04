import bpy

import math
import mathutils

import gpu
import gpu_extras.batch

import copy

class DrawCollider:
    # 描画ハンドル
    handle = None

    def draw_collider():
        """3Dビューに登録する描画関数"""
        
        # 3D空間描画用のシェーダを取得 
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")

        # 頂点データとインデックスデータ
        vertices = []
        indices = []

        # 各頂点のオブジェクトの中心からのオフセット
        offsets = [
            [-0.5, -0.5, -0.5], # 左下前
            [+0.5, -0.5, -0.5], # 右下前
            [-0.5, +0.5, -0.5], # 左上前
            [+0.5, +0.5, -0.5], # 右上前
            [-0.5, -0.5, +0.5], # 左下奥
            [+0.5, -0.5, +0.5], # 右下奥
            [-0.5, +0.5, +0.5], # 左上奥
            [+0.5, +0.5, +0.5], # 右上奥
        ]

        # 立方体のX, Y, Z方向サイズ
        size = [2, 2, 2]

        # 現在のシーンのオブジェクトリストを走査
        for object in bpy.context.scene.objects:

            # コライダープロパティがなければ描画をスキップ
            if not "collider" in object:
                continue

            # 中心点、サイズの変数宣言
            center = mathutils.Vector((0, 0, 0))
            size = mathutils.Vector((2, 2, 2))

            # プロパティから値を取得
            for i in range(3):
                center[i] = object["collider_center"][i]
                size[i] = object["collider_size"][i]

            # 追加前の頂点数
            start = len(vertices)

            # Boxの8頂点分回す
            for offset in offsets:
                # オブジェクトの中心座標をコピー
                pos = copy.copy(center)
                # 中心座標を基準に拡張店ごとにずらす
                for i in range(3):
                    pos[i] += offset[i] * size[i]    

                # ローカル座標からワールド座標に変換
                pos = object.matrix_world @ pos            

                # 頂点データリストに座標を追加
                vertices.append(pos)

            # 前面を構成する辺の頂点インデックス
            indices.append([start + 0, start + 1])
            indices.append([start + 2, start + 3])
            indices.append([start + 0, start + 2])
            indices.append([start + 1, start + 3])

            # 奥面を構成する辺の頂点インデックス
            indices.append([start + 4, start + 5])
            indices.append([start + 6, start + 7])
            indices.append([start + 4, start + 6])
            indices.append([start + 5, start + 7])

            # 手面を構成する辺の頂点インデックス
            indices.append([start + 0, start + 4])
            indices.append([start + 1, start + 5])
            indices.append([start + 2, start + 6])
            indices.append([start + 3, start + 7])

        if not vertices:
            return

        # 頂点フォーマット（GPUVertexFormat）を明示的に作成
        # "pos" という名前に、3次元(3)の浮動小数点("F32")が入ることを教える
        fmt = gpu.types.GPUVertFormat()
        fmt.attr_add(id="pos", comp_type="F32", len=3, fetch_mode="FLOAT")

        # フォーマットに沿ってVBO（頂点バッファオブジェクト）を作成
        vbo = gpu.types.GPUVertBuf(len=len(vertices), format=fmt)
        vbo.attr_fill(id="pos", data=vertices)

        # インデックスバッファ（IBO）を作成
        ibo = gpu.types.GPUIndexBuf(type="LINES", seq=indices)

        # シェーダ、VBO、IBOを組み合わせてバッチを作成
        batch = gpu.types.GPUBatch(type="LINES", buf=vbo, elem=ibo)

        # バインドして描画
        shader.bind()
        
        # 色の設定 (R, G, B, A)
        color = [0.5, 1.0, 1.0, 1.0]
        shader.uniform_float("color", color)
        
        batch.draw(shader)