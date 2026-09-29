shader_type spatial;
render_mode specular_disabled;

// Endless meadow drawn on a single quad: every world-space cell of `cell_size`
// gets its own shade, like the top of a field of voxels.

uniform vec3 grass_a : source_color = vec3(0.27, 0.52, 0.14);
uniform vec3 grass_b : source_color = vec3(0.40, 0.65, 0.20);
uniform vec3 dirt : source_color = vec3(0.50, 0.37, 0.21);
uniform float cell_size = 0.5;

varying vec3 world_pos;

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

float value_noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash12(i);
	float b = hash12(i + vec2(1.0, 0.0));
	float c = hash12(i + vec2(0.0, 1.0));
	float d = hash12(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 cell = floor(world_pos.xz / cell_size);
	vec2 centre = (cell + 0.5) * cell_size;   // everything is sampled per cell: flat voxel tops
	float h = hash12(cell);

	// Large meadow patches plus mid-scale mottling.
	float broad = value_noise(centre * 0.05);
	float mid = value_noise(centre * 0.30);
	vec3 col = mix(grass_a, grass_b, smoothstep(0.25, 0.75, broad * 0.65 + mid * 0.35));

	// Bare earth patches with a ragged, voxel-stepped edge.
	float bare = step(0.82 + (h - 0.5) * 0.10, value_noise(centre * 0.08 + 53.0));
	col = mix(col, dirt, bare);

	// Per-voxel speckle, faded with distance so it does not shimmer.
	float near = 1.0 - smoothstep(10.0, 40.0, length(VERTEX));
	col *= 1.0 + (h - 0.5) * 0.24 * near;

	// Tiny flowers, one voxel each.
	float f = hash12(cell + vec2(91.7, 13.3));
	if (f > 0.985 && bare < 0.5) {
		float k = hash12(cell + vec2(3.1, 7.9));
		vec3 flower = k < 0.33 ? vec3(0.95, 0.92, 0.85) : (k < 0.66 ? vec3(0.96, 0.82, 0.22) : vec3(0.85, 0.45, 0.70));
		col = mix(col, flower, near);
	}

	ALBEDO = col;
	ROUGHNESS = 1.0;
}
