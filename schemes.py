# -*- coding: utf-8 -*-
from __future__ import annotations

# Parameters are aligned with the packaged V3.0 executable, not the loose tools
# script. The first-stage SoX schemes intentionally use pitch + 44.1k output;
# using the older tempo+bend set changes duration/loudness and drifts in combos.

SCHEMES = [
    {
        "index": 1, "num": "推荐一", "id": "H", "name": "推荐一：音质无损",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "轻量底层处理，保留主体、人声和旋律，适合作为组合第一步。",
        "engine": "sox", "role": "轻修保真",
        "sox_args": ["highpass", "28", "pitch", "-25", "treble", "-0.32", "8500",
                     "treble", "0", "7000", "treble", "-3", "9000", "treble", "-6", "10000",
                     "lowpass", "10000", "reverb", "20", "40", "55", "60",
                     "gain", "-n", "-1.8", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 2, "num": "推荐二", "id": "I", "name": "推荐二：无损升级",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "在方案一基础上补低频，适合组合收尾或整体偏薄的素材。",
        "engine": "sox", "role": "厚度补偿",
        "sox_args": ["highpass", "28", "pitch", "-25", "bass", "4",
                     "treble", "-0.32", "8500", "treble", "0", "7000",
                     "treble", "-3", "9000", "treble", "-6", "10000",
                     "lowpass", "10000", "reverb", "20", "40", "55", "60",
                     "gain", "-n", "-1.8", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 3, "num": "推荐三", "id": "J", "name": "推荐三：自由实验",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "低频和空间更明显，适合需要更强底层变化的素材。",
        "engine": "sox", "role": "低频重塑",
        "sox_args": ["highpass", "28", "pitch", "-25", "bass", "4",
                     "treble", "-0.32", "8500", "treble", "0", "6000",
                     "treble", "-3", "8000", "treble", "-6", "9000",
                     "lowpass", "9000", "reverb", "25", "45", "55", "65",
                     "gain", "-n", "-1.8", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 4, "num": "推荐四", "id": "K", "name": "推荐四：稳定过载",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "温和过载与高频收束，适合数码味重但不想大幅损伤的素材。",
        "engine": "sox", "role": "谐波收束",
        "sox_args": ["highpass", "28", "pitch", "-25", "bass", "5",
                     "treble", "-0.32", "8500", "treble", "0", "10000",
                     "treble", "-3", "12000", "treble", "-7", "14000",
                     "lowpass", "14000", "overdrive", "2", "80",
                     "reverb", "20", "45", "55", "65",
                     "gain", "-n", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 5, "num": "推荐五", "id": "L", "name": "推荐五：高频保真",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "保留更多空气感与高频细节，适合原曲音质较好的素材。",
        "engine": "sox", "role": "高频保真",
        "sox_args": ["highpass", "28", "pitch", "-25", "bass", "4",
                     "treble", "-0.1", "9500", "treble", "0", "13000",
                     "treble", "-2", "15000", "treble", "-5", "17500",
                     "lowpass", "17500", "overdrive", "2", "80",
                     "reverb", "30", "52", "60", "70",
                     "gain", "-n", "-1.5", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 6, "num": "推荐六", "id": "F", "name": "推荐六：SoX标准",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "中度高频整理与空间调整，适合偏硬、偏亮的素材。",
        "engine": "sox", "role": "空间均衡",
        "sox_args": ["pitch", "-25", "highpass", "40", "bass", "5",
                     "treble", "-3", "4500", "treble", "-5", "7000",
                     "treble", "-8", "12000", "treble", "0", "6000",
                     "treble", "-3", "8000", "treble", "-6", "9000",
                     "lowpass", "9000", "reverb", "25", "50", "60", "70",
                     "dither", "-s", "rate", "44100", "gain", "-n", "-2"],
    },
    {
        "index": 7, "num": "推荐七", "id": "G", "name": "推荐七：通用均衡",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "比方案六保留更多高频，适合曲谱和人声都要稳的素材。",
        "engine": "sox", "role": "曲谱均衡",
        "sox_args": ["pitch", "-25", "highpass", "40", "bass", "4",
                     "treble", "0", "5000", "treble", "-3", "8000",
                     "treble", "-7", "12000", "treble", "0", "8000",
                     "treble", "-3", "10000", "treble", "-6", "11000",
                     "lowpass", "11000", "reverb", "25", "40", "50", "60",
                     "gain", "-n", "-2", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 8, "num": "推荐八", "id": "H", "name": "推荐八：重低频",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "低频更厚、空间更深，适合声音很薄或中高频刺的素材。",
        "engine": "sox", "role": "厚度修正",
        "sox_args": ["tempo", "1.0185", "pitch", "-25", "highpass", "40",
                     "bass", "6", "treble", "0", "5000", "treble", "-3", "8000",
                     "treble", "-7", "12000", "lowpass", "9000",
                     "reverb", "30", "60", "70", "80",
                     "gain", "-n", "-2", "rate", "44100", "dither", "-s"],
    },
    {
        "index": 9, "num": "推荐九", "id": "B", "name": "推荐九：空气感保留",
        "tag": "推荐", "tag_bg": "#0d2137", "tag_fg": "#00e5ff",
        "desc": "保留全频段空气感和瞬态信息，适合作为 1-9 组合收尾。",
        "engine": "ffmpeg", "role": "空气收尾",
        "af": ("rubberband=pitch=0.975,"
               "equalizer=f=80:g=4.0:width_type=h:width=80,"
               "equalizer=f=150:g=3.0:width_type=h:width=100,"
               "equalizer=f=300:g=-1.5:width_type=h:width=200,"
               "equalizer=f=1500:g=-1.0:width_type=h:width=400,"
               "equalizer=f=4000:g=3.5:width_type=h:width=2000,"
               "equalizer=f=8000:g=1.8:width_type=h:width=4000,"
               "aecho=0.8:0.5:35|45:0.2|0.15,volume=2.0,highpass=f=45,"
               "crystalizer=i=0.15,"
               "acompressor=threshold=-18dB:ratio=2.0:attack=10:release=120:makeup=1.5,"
               "loudnorm=I=-12.6:TP=-0.5:LRA=11"),
        "extra_args": ["-map_metadata", "-1", "-ar", "48000", "-ac", "2",
                       "-sample_fmt", "s32", "-acodec", "pcm_s24le"],
    },
    {
        "index": 10, "num": "十", "id": "C", "name": "纯净人声",
        "tag": "颤音", "tag_bg": "#1e1030", "tag_fg": "#a78bfa",
        "desc": "轻微颤音和声场整理，适合人声过直、过平的素材。",
        "engine": "ffmpeg", "role": "人声自然",
        "af": ("vibrato=f=5.0:d=0.04,"
               "equalizer=f=400:g=-1.0:width_type=h:width=200,"
               "equalizer=f=2500:g=1.5:width_type=h:width=1000,"
               "aecho=0.90:0.85:35|45:0.18|0.12,highpass=f=60,"
               "lowpass=f=8000:width_type=h:width=800:poles=2,crystalizer=i=0.15,"
               "acompressor=threshold=-16dB:ratio=1.8:attack=5:release=70:makeup=1.5,"
               "loudnorm=I=-14:TP=-1.5:LRA=11"),
        "extra_args": ["-map_metadata", "-1", "-ar", "44100", "-ac", "2", "-acodec", "pcm_s16le"],
        "force_mp3": True,
    },
    {
        "index": 11, "num": "十一", "id": "D", "name": "母带精调",
        "tag": "母带", "tag_bg": "#2a2110", "tag_fg": "#c9a84c",
        "desc": "多段 EQ 和动态精调，适合后期制作或二次整理。",
        "engine": "ffmpeg", "role": "母带整理",
        "af": ("vibrato=f=5.5:d=0.03,highpass=f=80,"
               "equalizer=f=100:g=2.5:width_type=h:width=60,"
               "equalizer=f=250:g=1.5:width_type=h:width=100,"
               "equalizer=f=600:g=-0.8:width_type=h:width=150,"
               "equalizer=f=2400:g=-1.0:width_type=h:width=1200,"
               "equalizer=f=5000:g=-2.0:width_type=h:width=2000,"
               "aecho=0.90:0.85:35|55:0.18|0.12,crystalizer=i=0.15,"
               "acompressor=threshold=-20dB:ratio=1.5:attack=5:release=70:makeup=2.5,"
               "loudnorm=I=-14:TP=-1.5:LRA=11"),
        "extra_args": ["-map_metadata", "-1", "-ar", "48000", "-ac", "2",
                       "-sample_fmt", "s32", "-acodec", "pcm_s24le"],
    },
    {
        "index": 12, "num": "十二", "id": "E", "name": "旗舰精修",
        "tag": "强效", "tag_bg": "#1a1200", "tag_fg": "#f0b429",
        "desc": "净化、瞬态和 EQ 加强，适合特征很重的音频专用。",
        "engine": "ffmpeg", "role": "强效修整",
        "af": ("afftdn=nf=-20,vibrato=f=5.0:d=0.035,highpass=f=80,"
               "equalizer=f=250:g=1.0:width_type=h:width=80,"
               "equalizer=f=500:g=0.8:width_type=h:width=120,"
               "equalizer=f=1200:g=3.5:width_type=h:width=600,"
               "equalizer=f=2500:g=2.0:width_type=h:width=1000,"
               "equalizer=f=3000:g=2.0:width_type=h:width=2000,"
               "equalizer=f=5000:g=1.5:width_type=h:width=2000,"
               "equalizer=f=8000:g=-2.0:width_type=h:width=4000,"
               "equalizer=f=11000:g=-5.0:width_type=h:width=4000,"
               "equalizer=f=14000:g=-10.0:width_type=h:width=4000,"
               "aecho=0.90:0.85:40|55:0.18|0.12,crystalizer=i=0.20,"
               "acompressor=threshold=-16dB:ratio=1.8:attack=5:release=70:makeup=1.5,"
               "equalizer=f=7000:g=1.5:width_type=s:width=1,loudnorm=I=-14:TP=-1.5:LRA=11"),
        "extra_args": ["-map_metadata", "-1", "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le"],
    },
    {
        "index": 13, "num": "十三", "id": "N", "name": "保真净化",
        "tag": "净化", "tag_bg": "#0d1e2e", "tag_fg": "#38bdf8",
        "desc": "频域降噪和高频保留，适合轻度整理和发布前净化。",
        "engine": "ffmpeg", "role": "噪声净化",
        "af": "afftdn=nf=-20,highpass=f=40,lowpass=f=17500",
        "extra_args": ["-ar", "44100", "-ac", "2", "-map_metadata", "-1", "-acodec", "pcm_s24le"],
    },
    {
        "index": 14, "num": "十四", "id": "O", "name": "商业发布",
        "tag": "保真", "tag_bg": "#1a3d25", "tag_fg": "#4ed87a",
        "desc": "双阶段净化取向，适合发布前做最后统一整理。",
        "engine": "ffmpeg", "role": "发布定稿",
        "af": "afftdn=nf=-20,highpass=f=40,lowpass=f=17500",
        "extra_args": ["-ar", "44100", "-ac", "2", "-map_metadata", "-1",
                       "-fflags", "+bitexact", "-acodec", "pcm_s24le"],
    },
    {
        "index": 15, "num": "十五", "id": "P", "name": "曲谱回稳",
        "tag": "曲谱", "tag_bg": "#10263d", "tag_fg": "#5eead4",
        "desc": "压住超低频漂移，补回中频旋律线，适合修后曲谱数值偏低的歌曲。",
        "engine": "ffmpeg", "role": "曲谱稳定",
        "af": ("highpass=f=48,"
               "equalizer=f=65:g=-5.5:width_type=h:width=45,"
               "equalizer=f=180:g=0.6:width_type=h:width=110,"
               "equalizer=f=520:g=1.1:width_type=h:width=420,"
               "equalizer=f=1600:g=1.7:width_type=h:width=1100,"
               "equalizer=f=3900:g=2.6:width_type=h:width=2500,"
               "equalizer=f=8200:g=1.4:width_type=h:width=4300,"
               "equalizer=f=15000:g=-1.2:width_type=h:width=5000,"
               "acompressor=threshold=-20dB:ratio=1.22:attack=18:release=180:makeup=1.0,"
               "alimiter=limit=0.988"),
        "extra_args": ["-map_metadata", "-1", "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le"],
    },
    {
        "index": 16, "num": "十六", "id": "Q", "name": "细节定稿",
        "tag": "定稿", "tag_bg": "#1f2937", "tag_fg": "#93c5fd",
        "desc": "轻度统一响度和空间细节，适合组合最后一步，尽量不再改变旋律。",
        "engine": "ffmpeg", "role": "最终定稿",
        "af": ("highpass=f=35,"
               "equalizer=f=90:g=-1.2:width_type=h:width=80,"
               "equalizer=f=300:g=0.5:width_type=h:width=220,"
               "equalizer=f=1200:g=0.7:width_type=h:width=900,"
               "equalizer=f=3200:g=1.1:width_type=h:width=1800,"
               "equalizer=f=7600:g=0.6:width_type=h:width=3600,"
               "acompressor=threshold=-21dB:ratio=1.16:attack=24:release=210:makeup=1.0,"
               "alimiter=limit=0.988"),
        "extra_args": ["-map_metadata", "-1", "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le"],
    },
]

SCHEME_BY_ID = {int(s["index"]): s for s in SCHEMES}
