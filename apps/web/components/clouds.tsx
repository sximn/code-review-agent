'use client'

import { useEffect, useRef, useState } from 'react'
// import PulseCardPane from '@/components/pulse-card-pane'

type RGB = [number, number, number]

type Settings = {
  scale: number
  speed: number
  evolve: number
  shear: number
  coverage: number
  softness: number
  warpStr: number
  vigStr: number
  grainAmt: number
  domainWarp: boolean
  depth: boolean
  vertFlow: boolean
  vignette: boolean
  grain: boolean
  sunrise: boolean
  cSky: RGB
  cCloud: RGB
  cShadow: RGB
  cGlow: RGB
}

const defaults: Settings = {
  scale: 2.5,
  speed: 3,
  evolve: 0.54,
  shear: 0.3,
  coverage: 0.42,
  softness: 0.21,
  warpStr: 0.6,
  vigStr: 0.8,
  grainAmt: 0.04,
  domainWarp: true,
  depth: true,
  vertFlow: true,
  vignette: false,
  grain: false,
  sunrise: false,
  cSky: [0x5e / 255, 0x85 / 255, 0xe8 / 255],
  cCloud: [0xfc / 255, 0xec / 255, 0xc7 / 255],
  cShadow: [0xe0 / 255, 0xeb / 255, 1],
  cGlow: [0x9d / 255, 0x78 / 255, 0x34 / 255],
}

const VS = `
attribute vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }
`

const FS = `
precision highp float;
uniform vec2 u_res;
uniform float u_time, u_scale, u_speed, u_evolve, u_shear;
uniform float u_coverage, u_softness, u_warpStr, u_vigStr, u_grainAmt;
uniform bool u_domainWarp, u_depth, u_vertFlow, u_vignette, u_grain, u_sunrise;
uniform vec3 u_cSky, u_cCloud, u_cShadow, u_cGlow;

float hash(vec3 p) {
  p = fract(p * vec3(127.1, 311.7, 74.7));
  p += dot(p, p.yzx + 19.19);
  return fract((p.x + p.y) * p.z);
}

float noise(vec3 p) {
  vec3 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(mix(hash(i), hash(i + vec3(1,0,0)), u.x),
        mix(hash(i + vec3(0,1,0)), hash(i + vec3(1,1,0)), u.x), u.y),
    mix(mix(hash(i + vec3(0,0,1)), hash(i + vec3(1,0,1)), u.x),
        mix(hash(i + vec3(0,1,1)), hash(i + vec3(1,1,1)), u.x), u.y), u.z);
}

float fbm(vec2 uv, float t, float shearBias) {
  float val = 0.0, amp = 0.5, freq = 1.0;
  float windX = u_speed * 0.08, windY = u_speed * 0.03;
  for (int i = 0; i < 7; i++) {
    float shear = shearBias * float(i) * u_shear * 0.04;
    vec3 p = vec3(uv * freq + vec2(t * (windX + shear), t * windY),
                  t * u_evolve * (0.08 + float(i) * 0.03));
    val += amp * noise(p);
    freq *= 2.1;
    amp *= 0.48;
  }
  return val;
}

void main() {
  vec2 uv = (gl_FragCoord.xy - 0.5 * u_res) / min(u_res.x, u_res.y);
  uv *= u_scale;
  if (u_vertFlow) uv.y += sin(u_time * 0.04 * u_speed) * 0.06;

  float t = u_time;
  vec2 warpedUV = uv;
  if (u_domainWarp) {
    vec2 warpOffset = vec2(
      fbm(uv + vec2(1.7, 9.2), t * 0.6, 0.5),
      fbm(uv + vec2(8.3, 2.8), t * 0.6, -0.5)
    );
    warpedUV = uv + u_warpStr * (warpOffset - 0.5);
  }

  float base = fbm(warpedUV, t, 0.5);
  float detail = fbm(warpedUV * 1.8 + vec2(3.1, 1.7), t, -0.3);
  float density = mix(base, detail, 0.35);
  if (u_depth) {
    float deep = fbm(warpedUV * 0.45 + vec2(5.0, 2.0), t * 0.4, 0.2);
    density = mix(density, deep, 0.22);
  }

  float lo = u_coverage - u_softness, hi = u_coverage + u_softness;
  float cloud = smoothstep(lo, hi, density);
  float shadowSample = fbm(warpedUV + vec2(0.08, -0.06), t, 0.5);
  float shadowMask = smoothstep(lo - 0.08, hi - 0.08, shadowSample);
  float lit = clamp(cloud - shadowMask * 0.45, 0.0, 1.0);

  vec3 col = u_cSky;
  col = mix(col, u_cShadow, cloud * (1.0 - lit * 0.15));
  col = mix(col, u_cCloud, cloud * lit);
  if (u_sunrise) {
    float glowFactor = (1.0 - cloud) * smoothstep(0.3, 0.55, density);
    float screenY = gl_FragCoord.y / u_res.y;
    float horizonGlow = pow(1.0 - abs(screenY - 0.38), 6.0) * 0.5;
    col += u_cGlow * (glowFactor * 0.55 + horizonGlow);
  }
  if (u_vignette) {
    vec2 vigUV = gl_FragCoord.xy / u_res - 0.5;
    float vig = 1.0 - dot(vigUV, vigUV) * u_vigStr * 2.5;
    col *= clamp(vig, 0.0, 1.0);
  }
  if (u_grain) {
    float g = hash(vec3(gl_FragCoord.xy, fract(t * 0.1))) - 0.5;
    col += u_grainAmt * g;
  }
  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`

function compileShader(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type)
  if (!shader) throw new Error('Could not create shader')
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const error = gl.getShaderInfoLog(shader) ?? 'Shader compilation failed'
    gl.deleteShader(shader)
    throw new Error(error)
  }
  return shader
}

function toHex([r, g, b]: RGB) {
  return `#${[r, g, b].map((value) => Math.round(value * 255).toString(16).padStart(2, '0')).join('')}`
}

function fromHex(hex: string): RGB {
  const value = Number.parseInt(hex.slice(1), 16)
  return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255]
}

export function CloudCanvas({ showControls = false }: { showControls?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const settingsRef = useRef<Settings>({ ...defaults })
  const [, refreshControls] = useState(0)

  useEffect(() => {
    const canvas = canvasRef.current
    const gl = canvas?.getContext('webgl', { antialias: false, powerPreference: 'high-performance' })
    if (!canvas || !gl) return

    let vertex: WebGLShader
    let fragment: WebGLShader
    let program: WebGLProgram
    try {
      vertex = compileShader(gl, gl.VERTEX_SHADER, VS)
      fragment = compileShader(gl, gl.FRAGMENT_SHADER, FS)
      program = gl.createProgram()!
      gl.attachShader(program, vertex)
      gl.attachShader(program, fragment)
      gl.linkProgram(program)
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program) ?? 'Program link failed')
    } catch (error) {
      console.error(error)
      return
    }

    gl.useProgram(program)
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW)
    const position = gl.getAttribLocation(program, 'a_pos')
    gl.enableVertexAttribArray(position)
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)

    const uniform = (name: string) => gl.getUniformLocation(program, name)
    const u = {
      res: uniform('u_res'), time: uniform('u_time'), scale: uniform('u_scale'), speed: uniform('u_speed'),
      evolve: uniform('u_evolve'), shear: uniform('u_shear'), coverage: uniform('u_coverage'), softness: uniform('u_softness'),
      warpStr: uniform('u_warpStr'), vigStr: uniform('u_vigStr'), grainAmt: uniform('u_grainAmt'),
      domainWarp: uniform('u_domainWarp'), depth: uniform('u_depth'), vertFlow: uniform('u_vertFlow'), vignette: uniform('u_vignette'),
      grain: uniform('u_grain'), sunrise: uniform('u_sunrise'), cSky: uniform('u_cSky'), cCloud: uniform('u_cCloud'),
      cShadow: uniform('u_cShadow'), cGlow: uniform('u_cGlow'),
    }

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const width = Math.max(1, Math.floor(canvas.clientWidth * dpr))
      const height = Math.max(1, Math.floor(canvas.clientHeight * dpr))
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width
        canvas.height = height
        gl.viewport(0, 0, width, height)
      }
    }
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(canvas)
    resize()

    let frame = 0
    const started = performance.now()
    const render = (now: number) => {
      const s = settingsRef.current
      gl.uniform2f(u.res, canvas.width, canvas.height)
      gl.uniform1f(u.time, (now - started) / 1000)
      gl.uniform1f(u.scale, s.scale); gl.uniform1f(u.speed, s.speed); gl.uniform1f(u.evolve, s.evolve)
      gl.uniform1f(u.shear, s.shear); gl.uniform1f(u.coverage, s.coverage); gl.uniform1f(u.softness, s.softness)
      gl.uniform1f(u.warpStr, s.warpStr); gl.uniform1f(u.vigStr, s.vigStr); gl.uniform1f(u.grainAmt, s.grainAmt)
      gl.uniform1i(u.domainWarp, s.domainWarp ? 1 : 0); gl.uniform1i(u.depth, s.depth ? 1 : 0)
      gl.uniform1i(u.vertFlow, s.vertFlow ? 1 : 0); gl.uniform1i(u.vignette, s.vignette ? 1 : 0)
      gl.uniform1i(u.grain, s.grain ? 1 : 0); gl.uniform1i(u.sunrise, s.sunrise ? 1 : 0)
      gl.uniform3fv(u.cSky, s.cSky); gl.uniform3fv(u.cCloud, s.cCloud); gl.uniform3fv(u.cShadow, s.cShadow); gl.uniform3fv(u.cGlow, s.cGlow)
      gl.drawArrays(gl.TRIANGLES, 0, 6)
      frame = requestAnimationFrame(render)
    }
    frame = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      gl.deleteBuffer(buffer)
      gl.deleteProgram(program)
      gl.deleteShader(vertex)
      gl.deleteShader(fragment)
    }
  }, [])

  const setValue = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    settingsRef.current[key] = value
    refreshControls((count) => count + 1)
  }

  const slider = (key: keyof Settings, label: string, min: number, max: number, step: number) => (
    <label className="block" key={key}>
      <span className="mb-1 flex justify-between"><span>{label}</span><span className="opacity-60">{Number(settingsRef.current[key]).toFixed(2)}</span></span>
      <input className="w-full accent-blue-300" type="range" min={min} max={max} step={step}
        value={Number(settingsRef.current[key])} onChange={(event) => setValue(key, Number(event.target.value) as never)} />
    </label>
  )

  const toggle = (key: keyof Settings, label: string) => (
    <label className="flex items-center justify-between" key={key}>
      <span>{label}</span><input type="checkbox" checked={Boolean(settingsRef.current[key])}
        onChange={(event) => setValue(key, event.target.checked as never)} />
    </label>
  )

  const color = (key: keyof Settings, label: string) => (
    <label className="flex items-center justify-between" key={key}>
      <span>{label}</span><input type="color" value={toHex(settingsRef.current[key] as RGB)}
        onChange={(event) => setValue(key, fromHex(event.target.value) as never)} />
    </label>
  )

  return (
    <div className="flex size-full justify-center items-center">
        <canvas ref={canvasRef} className="size-full rounded-2xl border-2 border-white/60" />
        {showControls && (
        <div className="absolute right-4 top-4 z-10 max-h-[calc(100%-2rem)] w-64 space-y-3 overflow-auto rounded-xl bg-black/60 p-4 font-mono text-xs text-white backdrop-blur-md">
            <div className="font-sans text-sm font-semibold">Cloud controls</div>
            {slider('scale', 'Scale', 0.5, 6, 0.01)}{slider('speed', 'Speed', 0, 10, 0.01)}
            {slider('evolve', 'Evolution', 0, 2, 0.01)}{slider('shear', 'Shear', -2, 2, 0.01)}
            {slider('coverage', 'Coverage', 0, 1, 0.01)}{slider('softness', 'Softness', 0.01, 0.6, 0.01)}
            {slider('warpStr', 'Warp strength', 0, 2, 0.01)}{slider('vigStr', 'Vignette strength', 0, 2, 0.01)}
            {slider('grainAmt', 'Grain amount', 0, 0.3, 0.001)}
            <div className="space-y-2 border-t border-white/20 pt-3">{toggle('domainWarp', 'Domain warp')}{toggle('depth', 'Depth')}{toggle('vertFlow', 'Vertical flow')}{toggle('vignette', 'Vignette')}{toggle('grain', 'Grain')}{toggle('sunrise', 'Sunrise')}</div>
            <div className="space-y-2 border-t border-white/20 pt-3">{color('cSky', 'Sky')}{color('cCloud', 'Cloud')}{color('cShadow', 'Shadow')}{color('cGlow', 'Glow')}</div>
            <button className="rounded bg-white/15 px-2 py-1 hover:bg-white/25" onClick={() => { settingsRef.current = { ...defaults }; refreshControls((count) => count + 1) }}>Reset</button>
        </div>
        )}
    </div>
  )
}

export default CloudCanvas

