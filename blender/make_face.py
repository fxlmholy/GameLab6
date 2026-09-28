from PIL import Image, ImageDraw, ImageFilter

S = 1024
SKIN = (242, 201, 160)
img = Image.new("RGB", (S, S), SKIN)
d = ImageDraw.Draw(img)

# ปรับขนาดตามสัดส่วน: ศูนย์กลางใบหน้าที่ (512, 560)
cx = S // 2
eye_y = 540
for side in (-1, 1):
    ex = cx + side * 150
    # ขาวตา
    d.ellipse([ex - 62, eye_y - 70, ex + 62, eye_y + 70], fill=(255, 255, 255), outline=(40, 30, 30), width=8)
    # ม่านตา
    d.ellipse([ex - 44, eye_y - 40, ex + 44, eye_y + 60], fill=(70, 45, 30))
    d.ellipse([ex - 24, eye_y - 12, ex + 24, eye_y + 40], fill=(15, 10, 10))
    # ไฮไลต์
    d.ellipse([ex - 30 + side * 4, eye_y - 30, ex - 6 + side * 4, eye_y - 6], fill=(255, 255, 255))
    d.ellipse([ex + 12, eye_y + 22, ex + 24, eye_y + 34], fill=(255, 255, 255))
    # คิ้ว
    bx0, bx1 = (ex - 70, ex + 70)
    d.line([(bx0, eye_y - 105 + (18 if side == -1 else 0)), (bx1, eye_y - 105 + (0 if side == -1 else 18))],
           fill=(45, 30, 25), width=22, joint="curve")
    # แก้มแดง
    blush = Image.new("L", (S, S), 0)
    ImageDraw.Draw(blush).ellipse([ex - 60 + side * 30, eye_y + 110, ex + 60 + side * 30, eye_y + 160], fill=120)
    blush = blush.filter(ImageFilter.GaussianBlur(18))
    img = Image.composite(Image.new("RGB", (S, S), (240, 130, 120)), img, blush)
    d = ImageDraw.Draw(img)

# จมูก
d.arc([cx - 22, 640, cx + 22, 690], start=20, end=160, fill=(200, 140, 110), width=8)
# ปากยิ้ม
d.chord([cx - 80, 700, cx + 80, 800], start=0, end=180, fill=(150, 50, 60), outline=(90, 30, 30), width=6)
d.rectangle([cx - 70, 700, cx + 70, 748], fill=SKIN)
d.chord([cx - 80, 700, cx + 80, 800], start=0, end=180, outline=(90, 30, 30), width=0)
d.arc([cx - 80, 700, cx + 80, 800], start=0, end=180, fill=(90, 30, 30), width=8)
d.chord([cx - 50, 752, cx + 50, 800], start=0, end=180, fill=(230, 110, 120))

img.save("/home/claude/work/face.png")
print("ok")
