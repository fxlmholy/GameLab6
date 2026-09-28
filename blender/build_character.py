"""สร้างตัวละคร low-poly + โครงกระดูกชื่อแบบ Mixamo ด้วย Blender (bpy) แล้ว export เป็น .glb"""
import math
import bpy
import bmesh
from mathutils import Vector

OUT = "/home/claude/work/character.glb"
FACE = "/home/claude/work/face.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---------------------------------------------------------------- Armature
P = "mixamorig_"
B = {}  # name -> (head, tail, parent)


def bone(name, h, t, parent=None):
    B[name] = (Vector(h), Vector(t), parent)


bone("Hips", (0, 0, 0.95), (0, 0, 1.05))
bone("Spine", (0, 0, 1.05), (0, 0, 1.15), "Hips")
bone("Spine1", (0, 0, 1.15), (0, 0, 1.27), "Spine")
bone("Spine2", (0, 0, 1.27), (0, 0, 1.40), "Spine1")
bone("Neck", (0, 0, 1.40), (0, 0, 1.49), "Spine2")
bone("Head", (0, 0, 1.49), (0, 0, 1.72), "Neck")
bone("HeadTop_End", (0, 0, 1.72), (0, 0, 1.82), "Head")
for s, sx in (("Left", 1), ("Right", -1)):
    bone(f"{s}Shoulder", (sx * 0.03, 0, 1.36), (sx * 0.16, 0, 1.37), "Spine2")
    bone(f"{s}Arm", (sx * 0.16, 0, 1.37), (sx * 0.43, 0, 1.37), f"{s}Shoulder")
    bone(f"{s}ForeArm", (sx * 0.43, 0, 1.37), (sx * 0.68, 0, 1.37), f"{s}Arm")
    bone(f"{s}Hand", (sx * 0.68, 0, 1.37), (sx * 0.76, 0, 1.37), f"{s}ForeArm")
    fingers = {"Thumb": (-0.035, -0.02), "Index": (-0.03, 0.0), "Middle": (-0.01, 0.0),
               "Ring": (0.01, 0.0), "Pinky": (0.03, 0.0)}
    for f, (fy, fz) in fingers.items():
        x0 = 0.70 if f == "Thumb" else 0.76
        prev = f"{s}Hand"
        for i in range(1, 5):
            h = (sx * (x0 + (i - 1) * 0.022), fy, 1.37 + fz)
            t = (sx * (x0 + i * 0.022), fy, 1.37 + fz)
            n = f"{s}Hand{f}{i}"
            bone(n, h, t, prev)
            prev = n
    bone(f"{s}UpLeg", (sx * 0.10, 0, 0.93), (sx * 0.10, 0, 0.52), "Hips")
    bone(f"{s}Leg", (sx * 0.10, 0, 0.52), (sx * 0.10, 0, 0.10), f"{s}UpLeg")
    bone(f"{s}Foot", (sx * 0.10, 0, 0.10), (sx * 0.10, -0.11, 0.03), f"{s}Leg")
    bone(f"{s}ToeBase", (sx * 0.10, -0.11, 0.03), (sx * 0.10, -0.19, 0.02), f"{s}Foot")
    bone(f"{s}Toe_End", (sx * 0.10, -0.19, 0.02), (sx * 0.10, -0.25, 0.02), f"{s}ToeBase")

arm_data = bpy.data.armatures.new("Armature")
arm = bpy.data.objects.new("Armature", arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for n, (h, t, par) in B.items():
    eb = arm_data.edit_bones.new(P + n)
    eb.head, eb.tail = h, t
    if par:
        eb.parent = arm_data.edit_bones[P + par]
        eb.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------- Materials


def mat(name, rgb, rough=0.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def srgb(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


M_SKIN = mat("Skin", srgb("F2C9A0"))
M_SHIRT = mat("Shirt", srgb("2E6FD8"))
M_PANTS = mat("Pants", srgb("2B2F3A"))
M_SHOE = mat("Shoes", srgb("F0F0F0"), 0.5)
M_HAIR = mat("Hair", srgb("241A16"), 0.5)
M_BELT = mat("Belt", srgb("7A4A22"))
M_FACE = bpy.data.materials.new("Face")
M_FACE.use_nodes = True
nt = M_FACE.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(FACE)
nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
MATS = [M_SKIN, M_SHIRT, M_PANTS, M_SHOE, M_HAIR, M_BELT, M_FACE]

# ---------------------------------------------------------------- Mesh helpers
bm = bmesh.new()
uv_layer = bm.loops.layers.uv.new("UVMap")
deform = bm.verts.layers.deform.new()
GROUPS = list(P + n for n in B)
GI = {g: i for i, g in enumerate(GROUPS)}


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


def assign(verts, bones):
    """rigid skinning: vertex -> nearest bone segment among candidates"""
    for v in verts:
        best = min(bones, key=lambda n: seg_dist(v.co, B[n][0], B[n][1]))
        v[deform][GI[P + best]] = 1.0


def tube(p0, p1, r0, r1, mat_i, bones, rings=4, seg=10, sx=1.0, sy=1.0, cap=True):
    p0, p1 = Vector(p0), Vector(p1)
    axis = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    w = axis.cross(u).normalized()
    loops = []
    for i in range(rings + 1):
        t = i / rings
        c = p0.lerp(p1, t)
        r = r0 + (r1 - r0) * t
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            off = u * math.cos(a) * r + w * math.sin(a) * r
            off = Vector((off.x * sx, off.y * sy, off.z))
            ring.append(bm.verts.new(c + off))
        loops.append(ring)
    faces = []
    for i in range(rings):
        for j in range(seg):
            a, b = loops[i][j], loops[i][(j + 1) % seg]
            c, d = loops[i + 1][(j + 1) % seg], loops[i + 1][j]
            faces.append(bm.faces.new((a, b, c, d)))
    if cap:
        faces.append(bm.faces.new(list(reversed(loops[0]))))
        faces.append(bm.faces.new(loops[-1]))
    for f in faces:
        f.material_index = mat_i
    verts = [v for r in loops for v in r]
    assign(verts, bones)
    return faces


def box(center, size, mat_i, bones, bevel_div=1):
    cx, cy, cz = center
    hx, hy, hz = (s / 2 for s in size)
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    for v in vs:
        v.co = Vector((cx + v.co.x * 2 * hx, cy + v.co.y * 2 * hy, cz + v.co.z * 2 * hz))
    fs = list({f for v in vs for f in v.link_faces})
    for f in fs:
        f.material_index = mat_i
    assign(vs, bones)
    return fs


def sphere(center, radius, mat_i, bones, scale=(1, 1, 1), segs=16, rings=12):
    r = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    vs = r["verts"]
    c = Vector(center)
    for v in vs:
        v.co = c + Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    fs = list({f for v in vs for f in v.link_faces})
    for f in fs:
        f.material_index = mat_i
    assign(vs, bones)
    return vs, fs


SKIN, SHIRT, PANTS, SHOE, HAIR, BELT, FACE_I = range(7)

# ---- ลำตัว (เสื้อ) : แบ่งหลาย ring ให้งอตาม Spine ได้
tube((0, 0, 0.98), (0, 0, 1.40), 0.155, 0.175, SHIRT,
     ["Hips", "Spine", "Spine1", "Spine2"], rings=8, seg=12, sy=0.68)
# ไหล่มน
for sx in (1, -1):
    sphere((sx * 0.17, 0, 1.36), 0.065, SHIRT, [("Left" if sx > 0 else "Right") + "Arm"], segs=10, rings=8)
# เข็มขัด + สะโพก
tube((0, 0, 0.90), (0, 0, 1.00), 0.160, 0.158, BELT, ["Hips"], rings=1, seg=12, sy=0.68)
tube((0, 0, 0.80), (0, 0, 0.92), 0.150, 0.160, PANTS, ["Hips"], rings=1, seg=12, sy=0.68)
# คอ
tube((0, 0, 1.38), (0, 0, 1.52), 0.05, 0.05, SKIN, ["Neck"], rings=1, seg=10)

for s, sx in (("Left", 1), ("Right", -1)):
    # แขนเสื้อ (ต้นแขน) + แขนท่อนล่าง (ผิว)
    tube((sx * 0.16, 0, 1.37), (sx * 0.30, 0, 1.37), 0.062, 0.058, SHIRT, [f"{s}Arm"], rings=1, seg=10)
    tube((sx * 0.30, 0, 1.37), (sx * 0.43, 0, 1.37), 0.045, 0.042, SKIN, [f"{s}Arm"], rings=1, seg=10)
    sphere((sx * 0.43, 0, 1.37), 0.043, SKIN, [f"{s}ForeArm"], segs=10, rings=6)
    tube((sx * 0.43, 0, 1.37), (sx * 0.67, 0, 1.37), 0.042, 0.035, SKIN, [f"{s}ForeArm"], rings=1, seg=10)
    # มือ + นิ้วโป้ง (มิตเทนแบบ low-poly)
    box((sx * 0.735, 0, 1.37), (0.10, 0.085, 0.035), SKIN, [f"{s}Hand"])
    box((sx * 0.715, -0.05, 1.365), (0.05, 0.03, 0.025), SKIN, [f"{s}Hand"])
    # ขา
    tube((sx * 0.10, 0, 0.90), (sx * 0.10, 0, 0.52), 0.080, 0.065, PANTS, [f"{s}UpLeg"], rings=2, seg=10)
    sphere((sx * 0.10, 0, 0.52), 0.064, PANTS, [f"{s}Leg"], segs=10, rings=6)
    tube((sx * 0.10, 0, 0.52), (sx * 0.10, 0, 0.12), 0.063, 0.052, PANTS, [f"{s}Leg"], rings=2, seg=10)
    # รองเท้า
    box((sx * 0.10, -0.035, 0.065), (0.11, 0.16, 0.10), SHOE, [f"{s}Foot"])
    box((sx * 0.10, -0.17, 0.035), (0.105, 0.12, 0.07), SHOE, [f"{s}ToeBase"])

# ---- ศีรษะ + UV ใบหน้า
HC = Vector((0, 0, 1.63))
HR = 0.145
_, head_faces = sphere(HC, HR, FACE_I, ["Head"], scale=(1, 0.95, 1.08), segs=24, rings=16)
for f in head_faces:
    front = f.normal.y < -0.05 and f.calc_center_median().y < -0.02
    for lp in f.loops:
        co = lp.vert.co
        if front:
            u = 0.5 + co.x / (2 * HR * 1.35)
            v = 0.50 + (co.z - HC.z) / (2 * HR * 1.4)
        else:
            u, v = 0.04, 0.04  # พื้นที่สีผิว
        lp[uv_layer].uv = (u, v)
# หู
for sx in (1, -1):
    sphere((sx * 0.145, 0.0, 1.62), 0.03, SKIN, ["Head"], scale=(0.5, 1, 1.3), segs=8, rings=6)

# ---- ผม : ครอบด้านบนและด้านหลัง เว้นหน้า
hv, hf = sphere(HC + Vector((0, 0.008, 0.012)), HR * 1.09, HAIR, ["Head"], scale=(1.02, 1.0, 1.08), segs=24, rings=16)
kill = []
for v in hv:
    rel = v.co - HC
    face_zone = rel.y < -0.035 and rel.z < 0.075
    low = rel.z < -0.06 and rel.y < 0.07
    very_low = rel.z < -0.13
    if face_zone or low or very_low:
        kill.append(v)
bmesh.ops.delete(bm, geom=kill, context="VERTS")
# ปอยผมหน้าม้า
sphere((0, -0.075, 1.725), 0.1, HAIR, ["Head"], scale=(1.35, 0.72, 0.42), segs=16, rings=8)
for x in (-0.07, 0.0, 0.07):
    sphere((x, -0.118, 1.70), 0.035, HAIR, ["Head"], scale=(1.1, 0.6, 1.1), segs=8, rings=6)

bm.normal_update()
me = bpy.data.meshes.new("Body")
bm.to_mesh(me)
bm.free()
for m in MATS:
    me.materials.append(m)
for f in me.polygons:
    f.use_smooth = True
body = bpy.data.objects.new("Body", me)
scene.collection.objects.link(body)
for g in GROUPS:
    body.vertex_groups.new(name=g)
body.parent = arm
mod = body.modifiers.new("Armature", "ARMATURE")
mod.object = arm

# ---- T-Pose action (1 ท่าตามที่ README ต้องการ)
arm.animation_data_create()
act = bpy.data.actions.new("TPose")
arm.animation_data.action = act
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
for pb in arm.pose.bones:
    pb.keyframe_insert("rotation_quaternion", frame=1)
    pb.keyframe_insert("location", frame=1)
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.wm.save_as_mainfile(filepath="/home/claude/work/character.blend")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_animations=True,
                          export_skins=True, export_yup=True, export_image_format="AUTO")
print("EXPORTED", OUT, len(me.vertices), "verts")
