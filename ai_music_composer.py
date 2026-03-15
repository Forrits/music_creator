# 导入所需库
from typing import Dict, TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import music21
import pygame
import tempfile
import os
import random
from dotenv import load_dotenv
import shutil  # 新增：用于保存MIDI文件

# 加载环境变量
load_dotenv()
# 设置 OpenAI API Key（兼容 DeepSeek）
os.environ["OPENAI_API_KEY"] = os.getenv('API_KEY', '')

# ======================== 1. 状态定义（扩展时长/BPM参数） ========================
class MusicState(TypedDict):
    """定义音乐生成工作流的状态结构"""
    musician_input: str          # 用户描述音乐的输入
    melody: str                  # 生成的旋律（music21格式）
    harmony: str                 # 生成的和声（music21格式）
    rhythm: str                  # 生成的节奏（music21格式）
    style: str                   # 期望的音乐风格
    composition: str             # 完整的音乐作品（music21格式）
    midi_file: str               # 生成的MIDI文件路径
    duration_seconds: int        # 新增：音乐总时长（秒）
    bpm: int                     # 新增：速度（每分钟拍数）
    save_midi_path: str          # 新增：保存MIDI文件的路径（可选）

# ======================== 2. 初始化LLM模型 ========================
def init_llm():
    """初始化LLM模型客户端"""
    try:
        llm = ChatOpenAI(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1/",
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=0.7  # 增加随机性，适配音乐创作
        )
        # 验证模型可用性
        response = llm.invoke("Hello, test connection")
        print("✅ LLM模型初始化成功！")
        return llm
    except Exception as e:
        print(f"❌ LLM模型初始化失败: {str(e)}")
        raise

# 初始化LLM实例
llm = init_llm()

# ======================== 3. 核心音乐生成函数 ========================
def melody_generator(state: MusicState) -> Dict:
    """基于用户输入生成旋律（适配自定义时长）"""
    prompt = ChatPromptTemplate.from_template(
        "Generate a {duration_seconds}-second melody based on this input: {input} (tempo: {bpm} BPM). "
        "Represent it as a string of notes in music21 format (e.g., C4 D4 E4 F4). "
        "Keep it musical and consistent with {style} style. Use {total_beats} notes (1 note per beat)."
    )
    # 计算总拍数
    total_beats = int(state["duration_seconds"] * (state["bpm"] / 60))
    chain = prompt | llm
    melody = chain.invoke({
        "input": state["musician_input"],
        "duration_seconds": state["duration_seconds"],
        "bpm": state["bpm"],
        "style": state["style"],
        "total_beats": total_beats
    })
    print("🎵 旋律生成完成")
    return {"melody": melody.content}

def harmony_creator(state: MusicState) -> Dict:
    """为生成的旋律创建和声"""
    prompt = ChatPromptTemplate.from_template(
        "Create harmony for this {style} style melody: {melody} (tempo: {bpm} BPM). "
        "Represent it as a string of chords in music21 format (e.g., Cmaj7 Fmaj7 G7). "
        "Ensure chords match the melody's rhythm and duration ({duration_seconds} seconds)."
    )
    chain = prompt | llm
    harmony = chain.invoke({
        "melody": state["melody"],
        "style": state["style"],
        "bpm": state["bpm"],
        "duration_seconds": state["duration_seconds"]
    })
    print("🎹 和声编排完成")
    return {"harmony": harmony.content}

def rhythm_analyzer(state: MusicState) -> Dict:
    """为旋律和和声分析并生成节奏"""
    prompt = ChatPromptTemplate.from_template(
        "Analyze and suggest a rhythm for this {style} style melody and harmony: {melody}, {harmony} "
        "(tempo: {bpm} BPM, duration: {duration_seconds} seconds). "
        "Represent it as a string of durations in music21 format (e.g., 1 1 0.5 0.5 2). "
        "Ensure rhythm fits the total duration."
    )
    chain = prompt | llm
    rhythm = chain.invoke({
        "melody": state["melody"],
        "harmony": state["harmony"],
        "style": state["style"],
        "bpm": state["bpm"],
        "duration_seconds": state["duration_seconds"]
    })
    print("🥁 节奏生成完成")
    return {"rhythm": rhythm.content}

def style_adapter(state: MusicState) -> Dict:
    """将作品适配指定的音乐风格"""
    prompt = ChatPromptTemplate.from_template(
        "Adapt this {duration_seconds}-second {style} style composition: "
        "Melody: {melody}, Harmony: {harmony}, Rhythm: {rhythm} (tempo: {bpm} BPM). "
        "Provide the result in music21 format (notes + chords + durations). Keep it musical and coherent."
    )
    chain = prompt | llm
    adapted = chain.invoke({
        "style": state["style"],
        "melody": state["melody"],
        "harmony": state["harmony"],
        "rhythm": state["rhythm"],
        "duration_seconds": state["duration_seconds"],
        "bpm": state["bpm"]
    })
    print("🎼 风格适配完成")
    return {"composition": adapted.content}

def midi_converter(state: MusicState) -> Dict:
    """将音乐作品转换为MIDI文件（支持自定义时长/BPM）"""
    # 创建乐谱对象
    piece = music21.stream.Score()
    
    # 添加作品描述
    description = music21.expressions.TextExpression(state["composition"])
    piece.append(description)

    # 定义扩展的音阶和和弦库
    scales = {
        'C major': ['C', 'D', 'E', 'F', 'G', 'A', 'B'],
        'C minor': ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'Bb'],
        'C harmonic minor': ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'B'],
        'C melodic minor': ['C', 'D', 'Eb', 'F', 'G', 'A', 'B'],
        'C dorian': ['C', 'D', 'Eb', 'F', 'G', 'A', 'Bb'],
        'C phrygian': ['C', 'Db', 'Eb', 'F', 'G', 'Ab', 'Bb'],
        'C lydian': ['C', 'D', 'E', 'F#', 'G', 'A', 'B'],
        'C mixolydian': ['C', 'D', 'E', 'F', 'G', 'A', 'Bb'],
        'C locrian': ['C', 'Db', 'Eb', 'F', 'Gb', 'Ab', 'Bb'],
        'C whole tone': ['C', 'D', 'E', 'F#', 'G#', 'A#'],
        'C diminished': ['C', 'D', 'Eb', 'F', 'Gb', 'Ab', 'A', 'B'],
        'F major': ['F', 'G', 'A', 'Bb', 'C', 'D', 'E'],
        'G minor': ['G', 'A', 'Bb', 'C', 'D', 'Eb', 'F#'],
        'D major': ['D', 'E', 'F#', 'G', 'A', 'B', 'C#']
    }

    chords = {
        'C major': ['C4', 'E4', 'G4'],
        'C minor': ['C4', 'Eb4', 'G4'],
        'C diminished': ['C4', 'Eb4', 'Gb4'],
        'C augmented': ['C4', 'E4', 'G#4'],
        'C dominant 7th': ['C4', 'E4', 'G4', 'Bb4'],
        'C major 7th': ['C4', 'E4', 'G4', 'B4'],
        'C minor 7th': ['C4', 'Eb4', 'G4', 'Bb4'],
        'C half-diminished 7th': ['C4', 'Eb4', 'Gb4', 'Bb4'],
        'C fully diminished 7th': ['C4', 'Eb4', 'Gb4', 'A4'],
        'F major': ['F4', 'A4', 'C5'],
        'G minor': ['G4', 'Bb4', 'D5'],
        'D major': ['D4', 'F#4', 'A4']
    }

    # 辅助函数：生成旋律（支持自定义拍数）
    def create_melody(scale_name, total_beats):
        melody = music21.stream.Part()
        scale = scales[scale_name]
        # 生成指定拍数的旋律
        for _ in range(total_beats):
            note = music21.note.Note(random.choice(scale) + str(random.choice([4, 5])))  # 随机八度
            note.quarterLength = 1
            melody.append(note)
        return melody

    # 辅助函数：生成和弦进行（支持自定义拍数）
    def create_chord_progression(total_beats):
        harmony = music21.stream.Part()
        # 每2拍换一个和弦（更符合音乐规律）
        chords_per_beat = 2
        chord_count = total_beats // chords_per_beat
        remaining_beats = total_beats % chords_per_beat
        
        for i in range(chord_count):
            chord_name = random.choice(list(chords.keys()))
            chord = music21.chord.Chord(chords[chord_name])
            chord.quarterLength = chords_per_beat
            harmony.append(chord)
        
        # 处理剩余拍数
        if remaining_beats > 0:
            chord_name = random.choice(list(chords.keys()))
            chord = music21.chord.Chord(chords[chord_name])
            chord.quarterLength = remaining_beats
            harmony.append(chord)
        
        return harmony

    # 根据用户输入选择音阶
    user_input = state['musician_input'].lower()
    if 'minor' in user_input:
        if 'g minor' in user_input:
            scale_name = 'G minor'
        else:
            scale_name = 'C minor'
    elif 'major' in user_input:
        if 'f major' in user_input:
            scale_name = 'F major'
        elif 'd major' in user_input:
            scale_name = 'D major'
        else:
            scale_name = 'C major'
    else:
        scale_name = random.choice(list(scales.keys()))

    # ========== 核心优化：根据时长/BPM计算总拍数 ==========
    total_seconds = state["duration_seconds"]
    bpm = state["bpm"]
    total_beats = int(total_seconds * (bpm / 60))  # 总拍数 = 时长 × (BPM/60)
    
    # 生成旋律和和声
    melody = create_melody(scale_name, total_beats)
    harmony = create_chord_progression(total_beats)

    # 设置速度
    piece.insert(0, music21.tempo.MetronomeMark(number=bpm))

    # 添加旋律和和声到乐谱
    piece.append(melody)
    piece.append(harmony)

    # 创建临时MIDI文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_midi:
        piece.write('midi', temp_midi.name)
        midi_path = temp_midi.name

    # 可选：保存MIDI文件到指定路径
    if state.get("save_midi_path"):
        save_path = state["save_midi_path"]
        # 确保保存目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        shutil.copy(midi_path, save_path)
        print(f"💾 MIDI文件已保存到: {save_path}")

    print(f"📁 MIDI文件生成完成: {midi_path} (时长: {total_seconds}秒, 速度: {bpm}BPM, 总拍数: {total_beats})")
    return {"midi_file": midi_path}

# ======================== 4. MIDI播放函数（增强稳定性） ========================
def play_midi(midi_file_path):
    """播放生成的MIDI文件（带异常处理和进度提示）"""
    try:
        # 初始化pygame混音器（设置缓存大小避免卡顿）
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        # 加载MIDI文件
        pygame.mixer.music.load(midi_file_path)
        # 开始播放
        print("▶️ 开始播放音乐...")
        pygame.mixer.music.play()

        # 播放进度提示
        start_time = pygame.time.get_ticks()
        while pygame.mixer.music.get_busy():
            elapsed = (pygame.time.get_ticks() - start_time) / 1000
            print(f"⏱️ 播放中: {elapsed:.1f}秒", end='\r')
            pygame.time.Clock().tick(1)
        
        print("\n⏹️ 播放完成")
    except pygame.error as e:
        print(f"❌ Pygame播放错误: {str(e)}")
        print("提示：请确保系统已安装MIDI音频驱动，或使用MuseScore/VLC打开MIDI文件")
    except Exception as e:
        print(f"❌ 播放失败: {str(e)}")
    finally:
        # 清理资源
        pygame.mixer.quit()

# ======================== 5. 构建LangGraph工作流 ========================
def build_music_workflow():
    """构建音乐创作工作流"""
    # 初始化状态图
    workflow = StateGraph(MusicState)

    # 添加节点
    workflow.add_node("melody_generator", melody_generator)
    workflow.add_node("harmony_creator", harmony_creator)
    workflow.add_node("rhythm_analyzer", rhythm_analyzer)
    workflow.add_node("style_adapter", style_adapter)
    workflow.add_node("midi_converter", midi_converter)

    # 设置入口点
    workflow.set_entry_point("melody_generator")

    # 连接节点（定义执行顺序）
    workflow.add_edge("melody_generator", "harmony_creator")
    workflow.add_edge("harmony_creator", "rhythm_analyzer")
    workflow.add_edge("rhythm_analyzer", "style_adapter")
    workflow.add_edge("style_adapter", "midi_converter")
    workflow.add_edge("midi_converter", END)

    # 编译工作流
    app = workflow.compile()
    print("🔧 工作流编译完成")
    return app

# ======================== 6. 主函数（程序入口） ========================
def main():
    """主函数：运行AI音乐创作系统"""
    # 1. 构建工作流
    app = build_music_workflow()

    # 2. 定义用户输入（可自定义所有参数）
    inputs = {
        "musician_input": "Create a happy piano piece in C major with gentle rhythm",
        "style": "Romantic era",
        "duration_seconds": 60,  # 自定义时长：60秒
        "bpm": 75,               # 自定义速度：75BPM
        "save_midi_path": "./generated_music/happy_romantic_piano.mid"  # 保存路径
    }
    print(f"🎯 开始创作音乐，用户需求: {inputs['musician_input']}")
    print(f"⚙️ 配置：时长={inputs['duration_seconds']}秒, 速度={inputs['bpm']}BPM, 风格={inputs['style']}")

    # 3. 执行工作流
    try:
        result = app.invoke(inputs)
        
        # 4. 播放生成的音乐
        play_midi(result["midi_file"])

    except Exception as e:
        print(f"\n❌ 音乐创作失败: {str(e)}")
        # 打印详细错误信息（便于调试）
        import traceback
        traceback.print_exc()

# 程序入口
if __name__ == "__main__":
    main()
