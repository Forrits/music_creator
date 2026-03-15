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

# 加载环境变量
load_dotenv()
# 设置 OpenAI API Key（兼容 DeepSeek）
os.environ["OPENAI_API_KEY"] = os.getenv('API_KEY', '')

# ======================== 1. 状态定义 ========================
class MusicState(TypedDict):
    """定义音乐生成工作流的状态结构"""
    musician_input: str  # 用户描述音乐的输入
    melody: str          # 生成的旋律（music21格式）
    harmony: str         # 生成的和声（music21格式）
    rhythm: str          # 生成的节奏（music21格式）
    style: str           # 期望的音乐风格
    composition: str     # 完整的音乐作品（music21格式）
    midi_file: str       # 生成的MIDI文件路径

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
    """基于用户输入生成旋律"""
    prompt = ChatPromptTemplate.from_template(
        "Generate a melody based on this input: {input}. Represent it as a string of notes in music21 format (e.g., C4 D4 E4 F4). Keep it simple (8 notes max)."
    )
    chain = prompt | llm
    melody = chain.invoke({"input": state["musician_input"]})
    print("🎵 旋律生成完成")
    return {"melody": melody.content}

def harmony_creator(state: MusicState) -> Dict:
    """为生成的旋律创建和声"""
    prompt = ChatPromptTemplate.from_template(
        "Create harmony for this melody: {melody}. Represent it as a string of chords in music21 format (e.g., Cmaj7 Fmaj7 G7). Keep it simple (4 chords max)."
    )
    chain = prompt | llm
    harmony = chain.invoke({"melody": state["melody"]})
    print("🎹 和声编排完成")
    return {"harmony": harmony.content}

def rhythm_analyzer(state: MusicState) -> Dict:
    """为旋律和和声分析并生成节奏"""
    prompt = ChatPromptTemplate.from_template(
        "Analyze and suggest a rhythm for this melody and harmony: {melody}, {harmony}. Represent it as a string of durations in music21 format (e.g., 1 1 0.5 0.5 2). Keep it simple (8 durations max)."
    )
    chain = prompt | llm
    rhythm = chain.invoke({"melody": state["melody"], "harmony": state["harmony"]})
    print("🥁 节奏生成完成")
    return {"rhythm": rhythm.content}

def style_adapter(state: MusicState) -> Dict:
    """将作品适配指定的音乐风格"""
    prompt = ChatPromptTemplate.from_template(
        "Adapt this composition to the {style} style: Melody: {melody}, Harmony: {harmony}, Rhythm: {rhythm}. Provide the result in music21 format (notes + chords + durations). Keep it concise."
    )
    chain = prompt | llm
    adapted = chain.invoke({
        "style": state["style"],
        "melody": state["melody"],
        "harmony": state["harmony"],
        "rhythm": state["rhythm"]
    })
    print("🎼 风格适配完成")
    return {"composition": adapted.content}

def midi_converter(state: MusicState) -> Dict:
    """将音乐作品转换为MIDI文件"""
    # 创建乐谱对象
    piece = music21.stream.Score()
    
    # 添加作品描述
    description = music21.expressions.TextExpression(state["composition"])
    piece.append(description)

    # 定义音阶和和弦库
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
    }

    # 辅助函数：生成旋律
    def create_melody(scale_name, duration):
        melody = music21.stream.Part()
        scale = scales[scale_name]
        for _ in range(duration):
            note = music21.note.Note(random.choice(scale) + '4')
            note.quarterLength = 1
            melody.append(note)
        return melody

    # 辅助函数：生成和弦进行
    def create_chord_progression(duration):
        harmony = music21.stream.Part()
        for _ in range(duration):
            chord_name = random.choice(list(chords.keys()))
            chord = music21.chord.Chord(chords[chord_name])
            chord.quarterLength = 1
            harmony.append(chord)
        return harmony

    # 根据用户输入选择音阶
    user_input = state['musician_input'].lower()
    if 'minor' in user_input:
        scale_name = 'C minor'
    elif 'major' in user_input:
        scale_name = 'C major'
    else:
        scale_name = random.choice(list(scales.keys()))

    # 生成8小节的旋律和和声（60BPM，8拍）
    melody = create_melody(scale_name, 7)
    harmony = create_chord_progression(7)

    # 添加最后一个音符/和弦，凑齐8拍
    final_note = music21.note.Note(scales[scale_name][0] + '4')
    final_note.quarterLength = 1
    melody.append(final_note)
    
    final_chord = music21.chord.Chord(chords[f"{scale_name.split()[0]} {scale_name.split()[1]}"])
    final_chord.quarterLength = 1
    harmony.append(final_chord)

    # 添加旋律和和声到乐谱
    piece.append(melody)
    piece.append(harmony)

    # 设置速度为60BPM
    piece.insert(0, music21.tempo.MetronomeMark(number=60))

    # 创建临时MIDI文件
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as temp_midi:
        piece.write('midi', temp_midi.name)
        midi_path = temp_midi.name

    print(f"📁 MIDI文件生成完成: {midi_path}")
    return {"midi_file": midi_path}

# ======================== 4. MIDI播放函数 ========================
def play_midi(midi_file_path):
    """播放生成的MIDI文件"""
    try:
        # 初始化pygame混音器
        pygame.mixer.init()
        # 加载MIDI文件
        pygame.mixer.music.load(midi_file_path)
        # 开始播放
        print("▶️ 开始播放音乐...")
        pygame.mixer.music.play()

        # 等待播放完成
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        print("⏹️ 播放完成")
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

    # 2. 定义用户输入
    inputs = {
        "musician_input": "Create a happy piano piece in C major",
        "style": "Romantic era"
    }
    print(f"🎯 开始创作音乐，用户需求: {inputs['musician_input']} (风格: {inputs['style']})")

    # 3. 执行工作流
    try:
        result = app.invoke(inputs)
        
        # 4. 播放生成的音乐
        play_midi(result["midi_file"])

        # 可选：保留MIDI文件（默认是临时文件，程序退出后会被删除）
        # 如需保留，可将tempfile的delete=False改为True，或复制文件到指定路径
        # import shutil
        # shutil.copy(result["midi_file"], "./generated_music.mid")
        # print("📌 MIDI文件已保存到: ./generated_music.mid")

    except Exception as e:
        print(f"❌ 音乐创作失败: {str(e)}")

# 程序入口
if __name__ == "__main__":
    main()
