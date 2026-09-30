shader_type sky;

// A quiet, art-directed atmosphere; independent of real-time sky lighting.
void sky() {
	float height = clamp(EYEDIR.y * 2.6, 0.0, 1.0);
	vec3 horizon = vec3(0.84, 0.82, 0.66);
	vec3 zenith = vec3(0.40, 0.61, 0.65);
	COLOR = mix(horizon, zenith, pow(height, 0.65));
}
