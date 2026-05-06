# Icons

Drop two PNG files here before zipping the agent package:

- `color.png` — 192×192, full color
- `outline.png` — 32×32, transparent background, white silhouette

These are required by the Teams app manifest and Microsoft 365 will reject the
package if they are missing or the wrong dimensions.

You can generate placeholders with ImageMagick:

```bash
convert -size 192x192 xc:'#2A6DF4' agent/appPackage/color.png
convert -size 32x32 xc:none -fill white -draw "circle 16,16 16,4" agent/appPackage/outline.png
```
