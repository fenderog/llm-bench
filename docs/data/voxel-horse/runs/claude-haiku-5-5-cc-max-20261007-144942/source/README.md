# Voxel Horse

An endless gallop built in Godot 4.7. The horse, trees, rocks and hurdles are
all made of voxel cubes generated at runtime, so there are no external assets
or plugins.

## Run it

Either open the folder in the Godot 4.7 editor and press F5, or run it from a
terminal:

```sh
godot --path .
```

The main scene is `main.tscn`.

## Controls

| Key            | Action             |
| -------------- | ------------------ |
| A / D or ← / → | Steer left / right |
| W / S or ↑ / ↓ | Speed up / slow down |
| Space          | Jump               |
| R              | Restart            |

Time your jump so the horse's hooves are above the top rail when it reaches a
hurdle. Hitting one knocks it over and slows the horse down for a moment.

## Web export

The project uses the `gl_compatibility` renderer and does not enable thread
support. In the Web export preset, leave thread support turned off.
