#!/usr/bin/env python3
"""Create verified streaming and CD masters with reusable mastering presets."""
from __future__ import annotations
import argparse, json, math, re, shutil, subprocess, sys, wave
from copy import deepcopy
from pathlib import Path
from typing import Any

PRESETS = {
    "transparent": {"description":"Transparent delivery master.","eq":[],"compressor":{"enabled":False},"ms":{"enabled":False},"tape":{"enabled":False,"drive":0,"mix":0},"limiter":{"enabled":True,"threshold":-0.5,"ceiling":-1.0,"release":80,"knee":2},"target_lufs":-14.0,"target_lra":7.0,"true_peak":-1.0},
    "wide-transparent": {"description":"Controlled M/S widening without saturation.","eq":[],"compressor":{"enabled":False},"ms":{"enabled":True,"width":45,"side_low_cut":80,"side_level":2.5,"side_air":0,"mid_hi":0},"tape":{"enabled":False,"drive":0,"mix":0},"limiter":{"enabled":True,"threshold":-0.5,"ceiling":-1.0,"release":80,"knee":2},"target_lufs":-14.0,"target_lra":7.0,"true_peak":-1.0},
    "hybrid": {"description":"Moderate EQ, M/S width, and gentle Tape approximation.","eq":[{"freq":30,"gain":-2,"q":0.7,"type":"q"},{"freq":80,"gain":1.5,"q":1,"type":"q"},{"freq":400,"gain":-1,"q":1.5,"type":"q"},{"freq":2000,"gain":2,"q":1.2,"type":"q"},{"freq":5000,"gain":3.5,"q":1,"type":"q"},{"freq":10000,"gain":3,"q":0.8,"type":"q"},{"freq":16000,"gain":2.5,"q":0.7,"type":"h"}],"compressor":{"enabled":False},"ms":{"enabled":True,"width":55,"side_low_cut":80,"side_level":4,"side_air":2,"mid_hi":1.5},"tape":{"enabled":True,"drive":10,"mix":100},"limiter":{"enabled":True,"threshold":-1.5,"ceiling":-1.0,"release":80,"knee":2},"target_lufs":-14.0,"target_lra":7.0,"true_peak":-1.0},
    "wide-tape": {"description":"Bright, wide club-oriented Tape-style master.","eq":[{"freq":30,"gain":-2,"q":0.7,"type":"q"},{"freq":60,"gain":1,"q":1,"type":"q"},{"freq":300,"gain":-1,"q":1.5,"type":"q"},{"freq":2000,"gain":2,"q":1.2,"type":"q"},{"freq":5000,"gain":3.5,"q":1,"type":"q"},{"freq":10000,"gain":5.5,"q":0.8,"type":"q"},{"freq":16000,"gain":6,"q":0.7,"type":"h"}],"compressor":{"enabled":False},"ms":{"enabled":True,"width":60,"side_low_cut":80,"side_level":5,"side_air":5,"mid_hi":1.5},"tape":{"enabled":True,"drive":10,"mix":100},"limiter":{"enabled":True,"threshold":-2,"ceiling":-1,"release":80,"knee":2},"target_lufs":-14.0,"target_lra":7.0,"true_peak":-1.0},
}

def run(cmd, capture=False):
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE if capture else None,stderr=subprocess.STDOUT if capture else None)
    if p.returncode: raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout or ''}")
    return p.stdout or ""

def f(x): return f"{float(x):.6g}"
def json_block(s):
    m=re.search(r"\{\s*\"input_i\".*?^\}",s,re.S|re.M)
    if not m: raise RuntimeError("Could not parse loudnorm analysis")
    return json.loads(m.group(0))

def merge(a,b):
    out=deepcopy(a)
    for k,v in b.items(): out[k]=merge(out[k],v) if isinstance(v,dict) and isinstance(out.get(k),dict) else v
    return out

def validate(c):
    if not isinstance(c.get("eq",[]),list): raise ValueError("eq must be a list")
    for b in c.get("eq",[]):
        if "freq" not in b or "gain" not in b: raise ValueError("EQ bands require freq and gain")
        if float(b["freq"])<=0 or not -60<=float(b["gain"])<=60: raise ValueError("EQ band outside supported range")
    if c.get("ms",{}).get("enabled") and not 0<=float(c["ms"].get("width",0))<=100: raise ValueError("M/S width must be 0..100")
    for k in ("target_lufs","target_lra","true_peak"):
        if k not in c: raise ValueError(f"Missing {k}")

def eq(b):
    typ=b.get("type","q"); w=f(b.get("q",1)); g=f(b["gain"]); fr=f(b["freq"])
    return f"equalizer=f={fr}:width_type={'h' if typ in ('h','hs','l','ls') else 'q'}:width={w}:g={g}"

def build_filter(c):
    fs=[eq(b) for b in c.get("eq",[])]
    ms=c.get("ms",{})
    if ms.get("enabled"):
        fs += ["pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0-0.5*c1[ms]","[ms]channelsplit=channel_layout=stereo[mid][side]"]
        mid=[f"equalizer=f=8000:width_type=h:width=0.7:g={f(ms['mid_hi'])}"] if float(ms.get("mid_hi",0)) else ["anull"]
        side=[]
        if float(ms.get("side_low_cut",0)): side.append(f"highpass=f={f(ms['side_low_cut'])}:p=2")
        if float(ms.get("side_level",0)): side.append(f"volume={f(ms['side_level'])}dB")
        factor=1+float(ms.get("width",0))/100
        if factor!=1: side.append(f"volume={f(factor)}")
        if float(ms.get("side_air",0)): side.append(f"equalizer=f=8000:width_type=h:width=0.7:g={f(ms['side_air'])}")
        fs += [f"[mid]{','.join(mid)}[midp]",f"[side]{','.join(side or ['anull'])}[sidep]","[midp][sidep]amerge=inputs=2,pan=stereo|c0=c0+c1|c1=c0-c1"]
    comp=c.get("compressor",{})
    if comp.get("enabled"):
        th=10**(float(comp.get("threshold",-18))/20); makeup=10**(float(comp.get("makeup_db",0))/20)
        fs.append(f"acompressor=threshold={f(th)}:ratio={f(comp.get('ratio',1.2))}:attack={f(comp.get('attack',40))}:release={f(comp.get('release',200))}:knee={f(comp.get('knee',2))}:makeup={f(makeup)}:mix={f(comp.get('mix',1))}")
    tape=c.get("tape",{})
    if tape.get("enabled") and float(tape.get("drive",0))>0 and float(tape.get("mix",100))>0:
        d=max(0,min(100,float(tape["drive"]))); threshold=max(.75,.98-d/200); fs.append(f"volume={f(d*.03)}dB,asoftclip=type=tanh:threshold={f(threshold)}:output=1:param=1.1:oversample=4")
    lim=c.get("limiter",{})
    if lim.get("enabled",True):
        drive=max(0,-float(lim.get("threshold",-.5)))
        if drive: fs.append(f"volume={f(drive)}dB")
        ceiling=10**(float(lim.get("ceiling",-1))/20)
        fs.append(f"aresample=192000:resampler=soxr:precision=28,alimiter=limit={f(ceiling)}:attack=1:release={f(lim.get('release',80))}:level=false:latency=true")
    else: fs.append("aresample=192000:resampler=soxr:precision=28")
    return ",".join(fs)

def loud_stats(p,c):
    return json_block(run(["ffmpeg","-hide_banner","-nostats","-i",str(p),"-af",f"loudnorm=I={f(c['target_lufs'])}:TP={f(c['true_peak'])}:LRA={f(c['target_lra'])}:print_format=json","-f","null","-"],capture=True))

def norm(stats,c):
    return f"loudnorm=I={f(c['target_lufs'])}:TP={f(c['true_peak'])}:LRA={f(c['target_lra'])}:measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:offset={stats['target_offset']}:linear=true:print_format=summary"

def summary(p):
    out=run(["ffmpeg","-hide_banner","-nostats","-i",str(p),"-af","ebur128=peak=true","-f","null","-"],capture=True); lines=out.splitlines(); i=next((i for i,x in enumerate(lines) if "Summary:" in x),None); return "\n".join(lines[i:i+12]) if i is not None else "Unavailable"

def peak(p):
    out=run(["ffmpeg","-hide_banner","-nostats","-i",str(p),"-af","ebur128=peak=true","-f","null","-"],capture=True); m=re.search(r"Peak:\s+([^\s]+)",out); return m.group(1) if m else "Unavailable"

def stereo(p):
    import numpy as np
    with wave.open(str(p),"rb") as w: sw,ch,raw=w.getsampwidth(),w.getnchannels(),w.readframes(w.getnframes())
    if ch!=2: raise ValueError("Stereo metrics require 2 channels")
    if sw==3:
        b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3); x=(b[:,0].astype(np.int32)|(b[:,1].astype(np.int32)<<8)|(b[:,2].astype(np.int32)<<16)); x=np.where(x&0x800000,x-(1<<24),x).astype(np.float64).reshape(-1,2)
    else: x=np.frombuffer(raw,dtype={1:np.int8,2:np.int16,4:np.int32}[sw]).astype(np.float64).reshape(-1,2)
    mid=(x[:,0]+x[:,1])/2; side=(x[:,0]-x[:,1])/2
    return float(np.sqrt(np.mean(side**2))/max(np.sqrt(np.mean(mid**2)),1e-20)),float(np.corrcoef(x[:,0],x[:,1])[0,1])

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("input",type=Path,nargs="?"); ap.add_argument("-o","--output-dir",type=Path,default=Path("mastered")); ap.add_argument("--title"); ap.add_argument("--preset",choices=sorted(PRESETS),default="transparent"); ap.add_argument("--config",type=Path); ap.add_argument("--list-presets",action="store_true"); ap.add_argument("--target-lufs",type=float); ap.add_argument("--true-peak",type=float); ap.add_argument("--width",type=float); ap.add_argument("--side-level",type=float); ap.add_argument("--side-air",type=float); ap.add_argument("--side-low-cut",type=float); ap.add_argument("--tape-drive",type=float); ap.add_argument("--no-tape"); a=ap.parse_args()
    if a.list_presets:
        for k,v in PRESETS.items(): print(f"{k}: {v['description']}")
        return 0
    if a.input is None: ap.error("the following arguments are required: input")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None: raise SystemExit("FFmpeg and FFprobe are required")
    if not a.input.is_file(): raise SystemExit(f"Input not found: {a.input}")
    c=deepcopy(PRESETS[a.preset])
    if a.config: c=merge(c,json.loads(a.config.read_text()))
    if a.target_lufs is not None: c["target_lufs"]=a.target_lufs
    if a.true_peak is not None: c["true_peak"]=a.true_peak
    if any(x is not None for x in (a.width,a.side_level,a.side_air,a.side_low_cut)):
        c.setdefault("ms",{})["enabled"]=True
        for name,val in (("width",a.width),("side_level",a.side_level),("side_air",a.side_air),("side_low_cut",a.side_low_cut)):
            if val is not None: c["ms"][name]=val
    if a.tape_drive is not None: c.setdefault("tape",{}).update(enabled=True,drive=a.tape_drive)
    if a.no_tape: c.setdefault("tape",{})["enabled"]=False
    validate(c); a.output_dir.mkdir(parents=True,exist_ok=True); stem=re.sub(r"[^A-Za-z0-9._-]+","_",a.input.stem); title=a.title or a.input.stem; temp=a.output_dir/f".{stem}.pre_192k_f32.wav"
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(a.input),"-filter_complex",build_filter(c),"-c:a","pcm_f32le","-ar","192000",str(temp)])
    stats=loud_stats(temp,c); chain=norm(stats,c); streaming=a.output_dir/f"{stem}_{a.preset}_streaming_24bit_48k.wav"; cd=a.output_dir/f"{stem}_{a.preset}_CD_16bit_44k1.wav"; comment=f"Preset {a.preset}; target {c['target_lufs']} LUFS; ceiling {c['true_peak']} dBTP"
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(temp),"-af",chain+",aresample=48000:resampler=soxr:precision=28","-c:a","pcm_s24le","-ar","48000","-metadata",f"title={title}","-metadata",f"comment={comment}",str(streaming)])
    run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(temp),"-af",chain+",aresample=44100:resampler=soxr:precision=28:dither_method=triangular","-c:a","pcm_s16le","-ar","44100","-metadata",f"title={title}","-metadata",f"comment={comment}; final triangular dither",str(cd)])
    temp.unlink(missing_ok=True)
    print(f"Input: {a.input}\nPreset: {a.preset}\nResolved configuration:\n{json.dumps(c,indent=2)}\nMeasured pre-master loudnorm stats:\n{json.dumps(stats,indent=2)}")
    for p in (streaming,cd):
        w,co=stereo(p); print(f"\n{p}\n{summary(p)}\nExact true peak: {peak(p)}\nStereo width (Side-to-Mid RMS): {w:.3f}\nStereo correlation: {co:.3f}")
    print(f"\nCreated:\n{streaming}\n{cd}")

if __name__=="__main__":
    try: main()
    except (RuntimeError,OSError,ValueError,json.JSONDecodeError) as e: print(f"ERROR: {e}",file=sys.stderr); sys.exit(1)
