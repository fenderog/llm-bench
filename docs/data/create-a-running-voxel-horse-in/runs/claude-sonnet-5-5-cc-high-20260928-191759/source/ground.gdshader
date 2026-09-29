shader_type spatial;

// Endless voxel-style ground: a grid of flat coloured tiles that scrolls
// towards the camera at the horse's speed, with a dirt trail down the middle.

uniform float scroll = 0.0;

varying vec3 world_pos;

const float CELL = 0.5;

float hash(vec2 p) {
	p = mod(p, 256.0);
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec3 to_linear(vec3 c) {
	return pow(c, vec3(2.2));
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 q = vec2(world_pos.x, world_pos.z - scroll) / CELL;
	vec2 c = floor(q);
	float h = hash(c);

	float half_w = 3.0 + floor(hash(vec2(c.y, 11.0)) * 3.0);
	bool on_path = abs(c.x + 0.5) < half_w;

	vec3 col;
	if (on_path) {
		col = mix(vec3(0.56, 0.42, 0.27), vec3(0.47, 0.34, 0.21), h);
	} else {
		col = mix(vec3(0.27, 0.52, 0.16), vec3(0.37, 0.63, 0.22), h);
		float f = hash(c + vec2(7.3, 1.9));
		if (f > 0.965) {
			float k = hash(c + vec2(3.1, 5.7));
			col = k < 0.33 ? vec3(0.95, 0.9, 0.35) : (k < 0.66 ? vec3(0.95, 0.95, 0.95) : vec3(0.9, 0.35, 0.4));
		}
	}

	// Fade tiles to their average colour with distance so far ground doesn't shimmer.
	float d = length(world_pos - CAMERA_POSITION_WORLD);
	vec3 avg = on_path ? vec3(0.51, 0.38, 0.24) : vec3(0.32, 0.57, 0.19);
	col = mix(col, avg, smoothstep(12.0, 45.0, d));

	ALBEDO = to_linear(col);
	ROUGHNESS = 1.0;
}
