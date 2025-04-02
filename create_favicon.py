from PIL import Image, ImageDraw

# Create a 32x32 image with a transparent background
img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw a simple network-like icon
draw.ellipse([8, 8, 24, 24], fill=(65, 105, 225))  # Royal Blue circle
draw.line([0, 16, 32, 16], fill=(65, 105, 225), width=2)
draw.line([16, 0, 16, 32], fill=(65, 105, 225), width=2)

# Save as ICO file
img.save('static/favicon.ico', format='ICO')