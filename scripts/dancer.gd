extends Node3D
## ตัวละคร 1 ตัว: เลือกชื่อท่าใน Inspector (animation_name) แล้วจะเล่นวนไปเรื่อย ๆ

@export var animation_name: String = "MeleeLib/LightIdle"

@onready var anim: AnimationPlayer = $Character/AnimationPlayer


func _ready() -> void:
	# 1) ใส่ Animation Library (เหมือนเมนู Animation > Manage Animations > Add Library)
	anim.add_animation_library("MeleeLib", load("res://animations/MeleeLib.res"))
	anim.add_animation_library("ShooterLib", load("res://animations/ShooterLib.res"))

	# 2) ตั้งให้ท่าวนซ้ำ แล้วเล่น
	anim.get_animation(animation_name).loop_mode = Animation.LOOP_LINEAR
	anim.play(animation_name)
