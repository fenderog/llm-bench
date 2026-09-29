extends SceneTree

func _key(code: Key) -> InputEventKey:
	var ev := InputEventKey.new()
	ev.device = -1
	ev.physical_keycode = code
	return ev

func _action(keys: Array) -> Dictionary:
	var events: Array = []
	for k in keys:
		events.append(_key(k))
	return {"deadzone": 0.2, "events": events}

func _init() -> void:
	var actions := {
		"steer_left": [KEY_A, KEY_LEFT],
		"steer_right": [KEY_D, KEY_RIGHT],
		"speed_up": [KEY_W, KEY_UP],
		"slow_down": [KEY_S, KEY_DOWN],
		"jump": [KEY_SPACE],
		"cycle_camera": [KEY_C],
		"toggle_auto_jump": [KEY_J],
		"toggle_mute": [KEY_M],
		"toggle_help": [KEY_H],
	}
	for name in actions:
		ProjectSettings.set_setting("input/" + name, _action(actions[name]))
	var err := ProjectSettings.save()
	print("save err: ", err)
	quit()
