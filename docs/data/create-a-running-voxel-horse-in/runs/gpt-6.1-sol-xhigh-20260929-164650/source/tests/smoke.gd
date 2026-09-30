extends SceneTree

# Run: godot --headless --path . --script tests/smoke.gd
func _initialize() -> void:
	check.call_deferred()

func check() -> void:
	var game = load("res://main.tscn").instantiate()
	root.add_child(game)
	current_scene = game
	await process_frame
	game.set_process(false)
	game.audio.enabled = false
	assert(game.mode == game.Mode.TITLE)
	assert(game.horse.hips.size() == 4)
	assert(game.landscape.chunks.size() == 7)
	game.start_run()
	game.steer(1)
	assert(game.target_lane == 2)
	game.steer(-1)
	game.request_jump()
	assert(game.jump_velocity > 0)
	for i in 70:
		game._process(1.0 / 60.0)
	assert(game.jump_y == 0)
	assert(game.distance > 10)
	game.pause_run()
	var stopped_distance: float = game.distance
	game._process(.05)
	assert(game.distance == stopped_distance)
	game.resume_run()
	assert(game.mode == game.Mode.RUNNING)
	# Carrot collection and all three obstacle collisions.
	game.clear_objects()
	game.spawn_carrot(1, game.HORSE_Z, 1.1)
	game.update_objects(0, 0)
	assert(game.carrots > 0)
	game.distance = 123
	for i in 3:
		game.clear_objects()
		game.invulnerable = 0
		game.spawn_obstacle(1, game.HORSE_Z, "fence")
		game.update_objects(0, 0)
	assert(game.mode == game.Mode.ENDED)
	assert(game.best == 123)
	game.start_run()
	assert(game.life == 3 and game.carrots == 0 and game.distance == 0)
	assert(game.best == 123)
	game.return_to_title()
	assert(game.mode == game.Mode.TITLE)
	game.audio.stop_all()
	await process_frame
	print("SMOKE TEST PASSED: gallop, jumping, steering, pause, pickups, collisions, end, restart.")
	quit()
