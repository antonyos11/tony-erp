"""
سكريبت لتوليد أيقونات PWA بأحجام مختلفة
يتطلب تثبيت مكتبة Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

# المسار الحالي
ICONS_DIR = os.path.dirname(os.path.abspath(__file__))

# الأحجام المطلوبة
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

def create_icon(size):
    """إنشاء أيقونة بحجم محدد"""
    # إنشاء صورة جديدة
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # الألوان
    bg_color = (30, 58, 95)  # #1e3a5f
    accent_color = (0, 212, 170)  # #00d4aa
    
    # رسم الخلفية المستديرة
    padding = int(size * 0.1)
    radius = int(size * 0.2)
    draw.rounded_rectangle(
        [0, 0, size-1, size-1],
        radius=radius,
        fill=bg_color
    )
    
    # رسم المبنى الرئيسي
    building_width = int(size * 0.4)
    building_height = int(size * 0.45)
    building_x = (size - building_width) // 2
    building_y = int(size * 0.2)
    
    draw.rounded_rectangle(
        [building_x, building_y, building_x + building_width, building_y + building_height],
        radius=int(size * 0.02),
        fill=accent_color
    )
    
    # رسم النوافذ
    window_size = int(size * 0.06)
    window_gap = int(size * 0.03)
    window_start_y = building_y + int(size * 0.05)
    
    for row in range(3):
        for col in range(3):
            wx = building_x + int(size * 0.05) + col * (window_size + window_gap)
            wy = window_start_y + row * (window_size + window_gap)
            draw.rounded_rectangle(
                [wx, wy, wx + window_size, wy + window_size],
                radius=2,
                fill=bg_color
            )
    
    # رسم المباني الجانبية
    side_width = int(size * 0.12)
    side_height = int(size * 0.3)
    side_y = building_y + int(size * 0.1)
    
    # يسار
    draw.rounded_rectangle(
        [building_x - side_width - int(size * 0.03), side_y,
         building_x - int(size * 0.03), side_y + side_height],
        radius=int(size * 0.015),
        fill=(0, 212, 170, 150)
    )
    
    # يمين
    draw.rounded_rectangle(
        [building_x + building_width + int(size * 0.03), side_y,
         building_x + building_width + side_width + int(size * 0.03), side_y + side_height],
        radius=int(size * 0.015),
        fill=(0, 212, 170, 150)
    )
    
    # حفظ الصورة
    filename = f'icon-{size}x{size}.png'
    filepath = os.path.join(ICONS_DIR, filename)
    img.save(filepath, 'PNG')
    print(f'✅ تم إنشاء: {filename}')
    
    return filepath

def main():
    print('🎨 جاري إنشاء أيقونات PWA...\n')
    
    for size in SIZES:
        create_icon(size)
    
    print(f'\n✅ تم إنشاء {len(SIZES)} أيقونة بنجاح!')
    print(f'📁 المسار: {ICONS_DIR}')

if __name__ == '__main__':
    main()
