# 来源 https://github.com/OS984/DiscordBotBackend/blob/3b06b8be39e4dbc07722b0afefeee4c18c136102/NeuralTTS.py
# A completely innocent attempt to borrow proprietary Microsoft technology for a much better TTS experience
from dataclasses import dataclass
from copy import copy
from email.policy import default
from typing import Any
import string
import time
import requests
import websockets
import asyncio
from datetime import datetime
import time
import re
import uuid
import argparse
import yaml
from mako.template import Template
from pydub import AudioSegment
import os

# 一些限制，避免微软接口返回错误或者音频不完整
__MAX_COUNT = 350 # 每次发送请求最大的字数
__MAX_SSML_TOTAL = 800 # 每次发送请求最大的SSML格式化后字数
__SLEEP_S = 30 # 当失败时，等待多少秒重试

# 行首格式的前导符和结束符
__CHAR_LEAD = '【'
__CHAR_CLOSING = '】'

# SSML格式模板，支持填入 name rate pitch style role 和 text
__ssml_start = '<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="zh-CN">'
__ssml_end = '</speak>'
__ssml = [
    '<voice name="${name}"><prosody rate="${rate}%" pitch="${pitch}%">${text}</prosody></voice>',
    '<voice name="${name}"><mstts:express-as style="${style}"><prosody rate="${rate}%" pitch="${pitch}%">${text}</prosody></mstts:express-as></voice>',
    '<voice name="${name}"><mstts:express-as style="${style}" role="${role}"><prosody rate="${rate}%" pitch="${pitch}%">${text}</prosody></mstts:express-as></voice>'
]

# 一条SSML语音配置
@dataclass
class SSML:
    tag:str = ''
    name:str = 'zh-CN-XiaoxiaoNeural'
    desc:str = ''
    rate:int = 0
    pitch:int = 0
    style:str = None
    role:str = None

    def __eq__(self, __o: object) -> bool:
        return __o != None and self.tag == __o.tag and self.name == __o.name and self.rate == __o.rate and self.pitch == __o.pitch and self.style == __o.style and self.role == __o.role

'''
配置文件，yml格式，例如:

templates: # 语音模板
  - tag: g # 模板标签，用于匹配文本中的行首标签，比如【q】
    name: zh-CN-XiaoxiaoNeural # 微软合成引擎中的语音名称
    rate: 20 # 语速加减的百分比，20相当于 rate="20%"，可以是负数
    pitch: 10 # 语调
    style: chat # 风格
    role: boy # 角色
default: g # 默认语音配置，如果行首没有标签则使用默认语音配置
bitrate: 160k # 输出mp3的比特率
format: audio-24khz-160kbitrate-mono-mp3 # 语音格式
'''
@dataclass
class Config:
    templates: list[SSML]
    format:str = 'audio-24khz-160kbitrate-mono-mp3'
    bitrate:str = '160k'
    default:SSML = None
    tmpl = {}
    def __post_init__(self):
        data = []
        first = None
        for t in self.templates:
            ssml = SSML(**t)
            if first == None:
                first = ssml
            data.append(ssml)
            self.tmpl[ssml.tag] = ssml
        if self.default != None:
            ssml = self.tmpl[self.default]
            if ssml !=None:
                self.default = ssml
            else :
                self.default = first
        else :
            self.default = first


@dataclass
class Segment:
    filename:str
    count:int = 0
    total:int = 0
    lines:list[str] = None
    def __str__(self) -> str:
        return ''.join(self.lines)

'''命令行参数解析'''
def parseArgs():
    parser = argparse.ArgumentParser(description='text2speech')
    parser.add_argument('-i', '--input', dest='input', help='txt文件的路径，txt文件需要UTF-8编码', type=str, required=False)
    parser.add_argument('-c', '--config', dest='config', help='配置文件，yml格式', type=str, required=False)
    parser.add_argument('-o', '--output', dest='output', help='保存mp3文件的路径', type=str, required=False)
    args = parser.parse_args()

    return args


def load_config(path) -> Config:
    '''加载配置文件'''
    with open(path, 'r', encoding='utf-8') as file:
        cfg = yaml.safe_load(file.read())
        return Config(**cfg)

def str_count(ss) -> int:
    '''找出字符串中的中英文、空格、数字、标点符号个数'''
    count_en = count_dg = count_sp = count_zh = count_pu = 0
    for s in ss:
        # 英文
        if s in string.ascii_letters:
            count_en += 1
        # 数字
        elif s.isdigit():
            count_dg += 1
        # 空格
        elif s.isspace():
            count_sp += 1
        # 中文
        elif s.isalpha():
            count_zh += 1
        # 特殊字符
        else:
            count_pu += 1
    return count_en + count_zh

# Fix the time to match Americanisms
def hr_cr(hr):
    corrected = (hr - 1) % 24
    return str(corrected)

# Add zeros in the right places i.e 22:1:5 -> 22:01:05
def fr(input_string):
    corr = ''
    i = 2 - len(input_string)
    while (i > 0):
        corr += '0'
        i -= 1
    return corr + input_string

# Generate X-Timestamp all correctly formatted
def getXTime():
    now = datetime.now()
    return fr(str(now.year)) + '-' + fr(str(now.month)) + '-' + fr(str(now.day)) + 'T' + fr(hr_cr(int(now.hour))) + ':' + fr(str(now.minute)) + ':' + fr(str(now.second)) + '.' + str(now.microsecond)[:3] + 'Z'

# Async function for actually communicating with the websocket
async def transferMsTTSData(seg:Segment, cfg:Config):
    # endpoint1 = "https://azure.microsoft.com/en-gb/services/cognitive-services/text-to-speech/"
    # r = requests.get(endpoint1)
    # main_web_content = r.text
    # # They hid the Auth key assignment for the websocket in the main body of the webpage....
    # token_expr = re.compile('token: \"(.*?)\"', re.DOTALL)
    # Auth_Token = re.findall(token_expr, main_web_content)[0]
    # req_id = str('%032x' % random.getrandbits(128)).upper()
    # req_id is generated by uuid.
    req_id = uuid.uuid4().hex.upper()
    print(req_id)
    # wss://eastus.api.speech.microsoft.com/cognitiveservices/websocket/v1?TrafficType=AzureDemo&Authorization=bearer%20undefined&X-ConnectionId=577D1E595EEB45979BA26C056A519073
    # endpoint2 = "wss://eastus.tts.speech.microsoft.com/cognitiveservices/websocket/v1?Authorization=" + \
    #     Auth_Token + "&X-ConnectionId=" + req_id
    # 目前该接口没有认证可能很快失效
    endpoint2 = f"wss://eastus.api.speech.microsoft.com/cognitiveservices/websocket/v1?TrafficType=AzureDemo&Authorization=bearer%20undefined&X-ConnectionId={req_id}"
    async with websockets.connect(endpoint2) as websocket:
        payload_1 = '{"context":{"system":{"name":"SpeechSDK","version":"1.12.1-rc.1","build":"JavaScript","lang":"JavaScript","os":{"platform":"Browser/Linux x86_64","name":"Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0","version":"5.0 (X11)"}}}}'
        message_1 = 'Path : speech.config\r\nX-RequestId: ' + req_id + '\r\nX-Timestamp: ' + \
            getXTime() + '\r\nContent-Type: application/json\r\n\r\n' + payload_1
        await websocket.send(message_1)

        payload_2 = '{"synthesis":{"audio":{"metadataOptions":{"sentenceBoundaryEnabled":false,"wordBoundaryEnabled":false},"outputFormat":"'+cfg.format+'"}}}'
        message_2 = 'Path : synthesis.context\r\nX-RequestId: ' + req_id + '\r\nX-Timestamp: ' + \
            getXTime() + '\r\nContent-Type: application/json\r\n\r\n' + payload_2
        await websocket.send(message_2)

        # payload_3 = '<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US"><voice name="' + voice + '"><mstts:express-as style="General"><prosody rate="'+spd+'%" pitch="'+ptc+'%">'+ msg_content +'</prosody></mstts:express-as></voice></speak>'
        payload_3 = f'{__ssml_start}{seg}{__ssml_end}'
        # print(f"begin convert to speech, file: {seg.filename}, count:{seg.count}, content:{seg}")
        message_3 = 'Path: ssml\r\nX-RequestId: ' + req_id + '\r\nX-Timestamp: ' + \
            getXTime() + '\r\nContent-Type: application/ssml+xml\r\n\r\n' + payload_3
        await websocket.send(message_3)

        # Checks for close connection message
        end_resp_pat = re.compile('Path:turn.end')
        audio_stream = b''
        while(True):
            try:
                response = await websocket.recv()
                # print('receiving...')
                # Make sure the message isn't telling us to stop
                if (re.search(end_resp_pat, str(response)) == None):
                    # Check if our response is text data or the audio bytes
                    if type(response) == type(bytes()):
                        # Extract binary data
                        try:
                            needle = b'Path:audio\r\n'
                            start_ind = response.find(needle) + len(needle)
                            audio_stream += response[start_ind:]
                        except:
                            pass
                else:
                    break
            except Exception as e:
                print(f'exception raised. send: {payload_3}')
                raise e
        with open(f'{seg.filename}', 'wb') as audio_out:
            audio_out.write(audio_stream)
        print(f"end convert to speech, file: {seg.filename}, count:{seg.count}")

async def mainSeq(segs,cfg):
    await transferMsTTSData(segs,cfg)

# def get_SSML(path):
#     with open(path,'r',encoding='utf-8') as f:
#         return f.read()

def get_SSML(text:str, ssml:SSML) -> str:
    tmp = ''
    if ssml.style!=None and ssml.role!=None:
        tmp = __ssml[2]
    elif ssml.style!=None :
        tmp = __ssml[1]
    else :
        tmp = __ssml[0]
    return Template(tmp).render(text=text, **vars(ssml))

def is_empty(s:str) ->bool:
    return s==None or len(s.strip())<1

def parse_line(s:str, cfg:Config):
    ssml:SSML = None
    prefix = None
    s = s.lstrip()
    content:str = s
    if s.startswith(__CHAR_LEAD):
        inx = s.find(__CHAR_CLOSING)
        if inx > 0 :
            prefix = s[1:inx]
            content = s[inx+1:].lstrip()
    if prefix != None:
        tags = prefix.split(':')
        if tags[0] in cfg.tmpl:
            ssml = copy(cfg.tmpl[tags[0]])
        else:
            ssml = copy(cfg.default)
        if len(tags) == 2:
            ps = tags[1].split(',')
            style = None
            role = None
            if len(ps) == 1:
                style = ps[0]
            elif len(ps) == 2:
                style = ps[0]
                role = ps[1]
            if not is_empty(style) or not is_empty(role):
                ssml.changed = True
                if not is_empty(style):
                    ssml.style = style
                if not is_empty(role):
                    ssml.role = role
    return ssml,content

def gen_Segs(lines:list[str], cfg:Config) ->list[Segment]:
    ssml = None
    segs = []
    text = ''
    file_index = 0
    file_prefix = uuid.uuid4().hex.upper()
    seg = Segment(filename=f'{file_prefix}-{file_index:0>2d}.mp3', count=0, lines=[])
    for line in lines:
        ss, cc = parse_line(line, cfg)

        if ss == None:
            ss = cfg.default
        if ssml == None:
            ssml = ss
        ssml_text = get_SSML(text, ssml)
        ssml_total = str_count(f'{seg}')+str_count(ssml_text)
        if seg.count+str_count(cc)>__MAX_COUNT or ssml_total+str_count(cc)>__MAX_SSML_TOTAL:
            # print(f'[{file_index} count:{seg.count}, total:{ssml_total}')
            if not is_empty(text):
                seg.lines.append(ssml_text)
                text = ''
            segs.append(seg)
            file_index += 1
            seg = Segment(filename=f'{file_prefix}-{file_index:0>2d}.mp3', count=0, lines=[])
        else:
            seg.count += str_count(cc)
        if ss != ssml:
            if not is_empty(text):
                seg.lines.append(ssml_text)
                text = ''
            ssml = ss
        text += cc
    if not is_empty(text):
        seg.lines.append(get_SSML(text, ssml))
        segs.append(seg)
    return segs

def read_lines(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.readlines()

def merge_audio(segs:list[Segment], cfg:Config) -> AudioSegment:
    audio = AudioSegment.empty()
    for seg in segs:
        mp3 = AudioSegment.from_mp3(seg.filename)
        audio += mp3
    return audio

def run(lines, cfg, output_path):
    segs = gen_Segs(lines, cfg)
    print(f'2. make ssml done, segs={len(segs)}')

    for seg in segs:
        s = f'{seg}'
        if not is_empty(s):
            try:
                asyncio.get_event_loop().run_until_complete(mainSeq(seg,cfg))
            except:
                # 如果失败，则等待一会后重试一次
                time.sleep(__SLEEP_S)
                if os.path.exists(seg.filename):
                    os.remove(seg.filename)
                asyncio.get_event_loop().run_until_complete(mainSeq(seg,cfg))
    print(f'3. request tts done, segs={len(segs)}')

    audio:AudioSegment = merge_audio(segs, cfg)
    audio.export(output_path, format='mp3', bitrate=cfg.bitrate)
    print(f'4. merge segs done, output: {output_path}')

    for seg in segs:
        os.remove(seg.filename)
    print(f'5. remove temp files done, completed')

def cmd():
    args = parseArgs()
    output_path = args.output if args.output else 'output_'+ str(int(time.time()*1000))+".mp3"
    config_path = args.config if args.config else 'config.yml'
    input_path = args.input if args.input else 'mnyz1_02.txt'
    # 1 读取配置文件
    cfg = load_config(config_path)
    # 2 读取文本文件
    lines = read_lines(input_path)
    print(f'1. read txt done, lines={len(lines)}')
    # 3 进行转换
    run(lines, cfg, output_path)

if __name__ == "__main__":
    cmd()
 

    # python tts.py --input SSML.xml
    # python tts.py --input SSML.xml --output 保存文件名