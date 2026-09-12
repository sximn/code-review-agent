"use client";

import { useEffect, useRef } from "react";
import styles from "./fluid-gradient.module.css";

type FluidGradientProps = {
  className?: string;
  intensity?: number;
  lineCount?: number;
};

const vertexShader = `
  attribute vec2 a_position;
  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

const fragmentShader = `
  precision highp float;

  uniform vec2 u_resolution;
  uniform float u_time;
  uniform vec2 u_pointer;
  uniform float u_intensity;
  uniform float u_lineCount;

  float hash21(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(hash21(i), hash21(i + vec2(1.0, 0.0)), f.x),
      mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0)), f.x),
      f.y
    );
  }

  void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    float aspect = u_resolution.x / max(u_resolution.y, 1.0);
    vec2 p = (uv - 0.5) * vec2(aspect, 1.0);

    float slow = u_time * 0.055;
    float n1 = noise(p * 2.35 + vec2(slow, -slow * 0.7));
    float n2 = noise(p * 4.2 - vec2(slow * 0.45, slow));
    float wave = sin(p.y * 5.5 + n1 * 2.8 + slow * 2.0) * 0.035;
    float flow = n1 * 0.6 + n2 * 0.4;
    float centerGlow = exp(-length((p - vec2(0.12, 0.03)) * vec2(1.1, 0.8)) * 2.25);
    float pointerGlow = exp(-length(p - (u_pointer - 0.5) * vec2(aspect, 1.0)) * 5.0) * 0.08;

    // vec3 charcoal = vec3(0.055, 0.065, 0.078);
    // vec3 slate = vec3(0.22, 0.25, 0.30);
    // vec3 mist = vec3(0.74, 0.78, 0.84);
    // vec3 ice = vec3(0.90, 0.94, 0.98);
    // vec3 blue = vec3(0.35, 0.49, 0.67);

    // vec3 color = mix(charcoal, slate, smoothstep(0.02, 0.68, uv.y + flow * 0.35));
    // color = mix(color, mist, smoothstep(0.30, 0.82, flow + uv.y * 0.20));
    // color = mix(color, ice, centerGlow * 0.64 + pointerGlow);
    // color += blue * (0.07 + centerGlow * 0.13) * u_intensity;
    
    vec3 charcoal = vec3(0.341176, 0.360784, 0.407843); // #575C68
    vec3 slate    = vec3(0.537255, 0.650980, 0.929412); // #89A6ED
    vec3 mist     = vec3(0.647059, 0.733333, 0.937255); // #A5BBEF
    vec3 ice      = vec3(0.901961, 0.941176, 0.980392); // #E6F0FA
    vec3 blue     = vec3(0.749020, 0.803922, 0.929412); // #BF CDED

    vec3 color = mix(charcoal, slate, smoothstep(0.02, 0.68, uv.y + flow * 0.35));
    color = mix(color, mist, smoothstep(0.30, 0.82, flow + uv.y * 0.20));
    color = mix(color, ice, centerGlow * 0.64 + pointerGlow);
    color += blue * (0.07 + centerGlow * 0.13) * u_intensity;

    // Narrow vertical prisms. Their centers are softly displaced by the flow.
    float distortedX = uv.x + wave * u_intensity + (n1 - 0.5) * 0.035;
    float cell = fract(distortedX * u_lineCount);
    float edge = min(cell, 1.0 - cell);
    float line = 1.0 - smoothstep(0.018, 0.060, edge);
    float lineLight = smoothstep(0.26, 0.72, n2 + uv.y * 0.25) * 0.26;
    float lineShade = smoothstep(0.00, 0.50, edge) * 0.11;
    color += vec3(0.92, 0.95, 1.0) * line * (0.22 + lineLight) * u_intensity;
    color -= vec3(0.08, 0.10, 0.14) * lineShade;

    // A subdued vignette keeps the effect usable behind landing-page content.
    float vignette = 1.0 - smoothstep(0.34, 0.86, length((uv - 0.5) * vec2(0.82, 0.92)));
    color *= 0.78 + vignette * 0.22;
    gl_FragColor = vec4(color, 1.0);
  }
`;

function createShader(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

export function FluidGradient({ className = "", intensity = 1, lineCount = 42 }: FluidGradientProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", { alpha: false, antialias: false });
    if (!gl) return;

    const vertex = createShader(gl, gl.VERTEX_SHADER, vertexShader);
    const fragment = createShader(gl, gl.FRAGMENT_SHADER, fragmentShader);
    if (!vertex || !fragment) return;
    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;

    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    gl.useProgram(program);
    const position = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

    const resolution = gl.getUniformLocation(program, "u_resolution");
    const time = gl.getUniformLocation(program, "u_time");
    const pointer = gl.getUniformLocation(program, "u_pointer");
    const amount = gl.getUniformLocation(program, "u_intensity");
    const lines = gl.getUniformLocation(program, "u_lineCount");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    let started = performance.now();
    let pointerX = 0.55;
    let pointerY = 0.5;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform2f(resolution, canvas.width, canvas.height);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    const move = (event: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      pointerX = (event.clientX - rect.left) / rect.width;
      pointerY = 1 - (event.clientY - rect.top) / rect.height;
    };
    canvas.addEventListener("pointermove", move, { passive: true });

    const render = (now: number) => {
      const elapsed = reducedMotion ? 0 : (now - started) / 1000;
      gl.uniform1f(time, elapsed);
      gl.uniform2f(pointer, pointerX, pointerY);
      gl.uniform1f(amount, Math.max(0, intensity));
      gl.uniform1f(lines, Math.max(12, lineCount * Math.min(canvas.width / Math.max(canvas.height, 1), 1.25)));
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      frame = reducedMotion ? 0 : requestAnimationFrame(render);
    };
    render(performance.now());

    return () => {
      observer.disconnect();
      canvas.removeEventListener("pointermove", move);
      if (frame) cancelAnimationFrame(frame);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertex);
      gl.deleteShader(fragment);
    };
  }, [intensity, lineCount]);

  return (
    <div className={`${styles.fluidGradient} ${className}`} aria-hidden="true">
      <canvas ref={canvasRef} className={styles.canvas} />
      <div className={styles.wash} />
    </div>
  );
}

export default FluidGradient;
